"""Engine adapter that runs the real TradingAgents graph (GEOALPHA_ENGINE=tradingagents)."""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any

from geoalpha.agents.graph import GeoAlphaTradingGraph, build_config
from geoalpha.agents.stage_map import StageTracker
from geoalpha.core.logging import run_id_var
from geoalpha.core.settings import Settings
from geoalpha.core.stages import STAGE_BY_KEY, TA_STAGE_KEYS
from geoalpha.db import repo
from geoalpha.runner.orchestrator import EngineContext, EngineResult, StageFailed

log = logging.getLogger(__name__)

_POLL_S = 1.0


class TradingAgentsEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, ctx: EngineContext) -> EngineResult:
        run = ctx.run
        config = build_config(
            data_dir=self.settings.resolved_data_dir,
            llm_provider=self.settings.llm_provider,
            deep_model=self.settings.deep_model,
            quick_model=self.settings.quick_model,
            max_debate_rounds=int(run.settings.get("max_debate_rounds", 1)),
        )
        graph = GeoAlphaTradingGraph(config, evidence_block=ctx.evidence_block)

        done: set[str] = {
            k for k in TA_STAGE_KEYS if repo.get_stage(run.run_id, k).status == "done"
        }
        started_at: dict[str, float] = {}

        def emit(stage: str, status: str, **kw: Any) -> None:
            if status == "running":
                started_at[stage] = time.monotonic()
            ctx.on_stage(stage, status, **kw)

        tracker = StageTracker(emit, already_done=done)

        # The graph runs on its own thread; this thread applies its events in order and
        # enforces per-stage timeouts (a blocked LLM call cannot be interrupted, but the
        # run is failed promptly and can be resumed from the checkpoint).
        inbox: queue.Queue[tuple[str, Any]] = queue.Queue()

        def target() -> None:
            run_id_var.set(run.run_id)
            try:
                final, rating = graph.run_with_events(
                    run.ticker,
                    run.analysis_date.isoformat(),
                    on_node=lambda n, phase, res: inbox.put(("node", (n, phase, res))),
                    on_state=lambda st: inbox.put(("state", st)),
                )
                inbox.put(("done", (final, rating)))
            except BaseException as exc:  # noqa: BLE001
                inbox.put(("error", exc))

        threading.Thread(target=target, name=f"ta-{run.run_id}", daemon=True).start()

        while True:
            try:
                kind, item = inbox.get(timeout=_POLL_S)
            except queue.Empty:
                self._check_timeouts(tracker, started_at)
                continue
            if kind == "state":
                tracker.update_state(item)
            elif kind == "node":
                node, phase, result = item
                if phase == "start":
                    tracker.node_started(node)
                else:
                    tracker.node_finished(node, result)
            elif kind == "error":
                stage = (tracker.running() or ["decision"])[0]
                log.error("TradingAgents failed during %s", stage, exc_info=item)
                raise StageFailed(stage, _user_message(item))
            elif kind == "done":
                final, rating = item
                tracker.update_state(final)
                tracker.finish_all()
                return EngineResult(
                    pm_text=str(final.get("final_trade_decision") or ""),
                    rating=rating,
                    quick_llm=graph.quick_thinking_llm,
                )
            self._check_timeouts(tracker, started_at)

    @staticmethod
    def _check_timeouts(tracker: StageTracker, started_at: dict[str, float]) -> None:
        now = time.monotonic()
        for stage in tracker.running():
            limit = STAGE_BY_KEY[stage].timeout_s
            if now - started_at.get(stage, now) > limit:
                raise StageFailed(stage, f"Timed out after {limit // 60} minutes")


def _user_message(exc: BaseException) -> str:
    text = str(exc)
    lowered = text.lower()
    if "api key" in lowered or "authentication" in lowered or "401" in lowered:
        return "The language-model provider rejected the API key."
    if "rate limit" in lowered or "429" in lowered:
        return "The language-model provider is rate limiting requests. Retry in a minute."
    if "timeout" in lowered or "timed out" in lowered:
        return "A data or model request timed out."
    return "The analysis step failed. Retry to resume from the last completed step."
