"""Stage pipeline for one run (research R1-R3).

pre-stages (geo, forecast) run concurrently, non-critical
    -> evidence block
    -> engine (TradingAgents, or the scripted fake) drives the 8 critical stages
    -> decision card (confidence + citations) finishes the `decision` stage
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from geoalpha.agents import decision_card, evidence
from geoalpha.core.logging import run_id_var
from geoalpha.core.stages import PRE_STAGE_KEYS, STAGE_BY_KEY, TERMINAL_STAGE
from geoalpha.db import repo
from geoalpha.runner import events

log = logging.getLogger(__name__)


class Unavailable(Exception):
    """The input legitimately does not exist (no snapshot for the date, too little history).
    Distinct from a failure: the stage ends `unavailable`, not `failed`."""


class StageFailed(Exception):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message


@dataclass(frozen=True)
class RunContext:
    run_id: str
    ticker: str
    analysis_date: date
    settings: dict[str, Any]


@dataclass
class PreStageResult:
    report_md: str | None = None
    payload: dict[str, Any] | None = None
    # Extra SSE event announcing the structured result (e.g. "forecast.ready").
    ready_event: tuple[str, dict[str, Any]] | None = None


PreStageFn = Callable[[RunContext], PreStageResult]
# Registered by the forecast (US3) and geo (US2) features. Unregistered -> `skipped`.
PRE_STAGES: dict[str, PreStageFn] = {}

OnStage = Callable[..., None]


@dataclass
class EngineResult:
    pm_text: str
    rating: str
    quick_llm: Any | None = None


@dataclass
class EngineContext:
    run: RunContext
    evidence_block: str
    resume: bool
    on_stage: OnStage
    extra: dict[str, Any] = field(default_factory=dict)


class Engine(Protocol):
    def run(self, ctx: EngineContext) -> EngineResult: ...


# --------------------------------------------------------------------------- stages


def set_stage(
    run_id: str,
    key: str,
    status: str,
    *,
    report_md: str | None = None,
    payload: dict[str, Any] | None = None,
    error: str | None = None,
    retryable: bool = True,
) -> None:
    """Persist a stage transition and publish its SSE event."""
    now = repo.utcnow()
    fields: dict[str, Any] = {"status": status}
    if status == "running":
        attempts = repo.get_stage(run_id, key).attempts + 1
        fields.update(started_at=now, finished_at=None, error=None, attempts=attempts)
        repo.update_stage(run_id, key, **fields)
        events.publish(run_id, "stage.started", {"stage": key, "attempt": attempts})
        return
    if status in TERMINAL_STAGE:
        fields["finished_at"] = now
    if report_md is not None:
        fields["report_md"] = report_md
    if payload is not None:
        fields["payload"] = payload
    if error is not None:
        fields["error"] = error
    repo.update_stage(run_id, key, **fields)
    if status == "done":
        events.publish(
            run_id, "stage.completed", {"stage": key, "report_md": report_md, "payload": payload}
        )
    elif status in ("failed", "unavailable"):
        events.publish(
            run_id,
            f"stage.{status}",
            {"stage": key, "message": error or "", "retryable": retryable},
        )
    elif status == "skipped":
        events.publish(
            run_id,
            "stage.completed",
            {"stage": key, "report_md": None, "payload": None, "status": "skipped"},
        )


def _run_pre_stage(ctx: RunContext, key: str) -> None:
    fn = PRE_STAGES.get(key)
    if fn is None:
        set_stage(ctx.run_id, key, "skipped")
        return
    timeout = STAGE_BY_KEY[key].timeout_s
    for attempt in (1, 2):  # one automatic retry (FR-005)
        set_stage(ctx.run_id, key, "running")
        try:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"pre-{key}") as ex:
                result = ex.submit(_with_run_id, ctx.run_id, fn, ctx).result(timeout=timeout)
        except Unavailable as exc:
            set_stage(ctx.run_id, key, "unavailable", error=str(exc), retryable=False)
            repo.add_missing_input(ctx.run_id, key)
            return
        except FutureTimeout:
            message = f"{STAGE_BY_KEY[key].label} timed out after {timeout} s"
        except Exception as exc:  # noqa: BLE001 - surfaced as a stage failure
            log.exception("pre-stage %s failed (attempt %d)", key, attempt)
            message = str(exc) or type(exc).__name__
        else:
            if result.ready_event:
                events.publish(ctx.run_id, *result.ready_event)
            set_stage(ctx.run_id, key, "done", report_md=result.report_md, payload=result.payload)
            return
        if attempt == 1:
            time.sleep(2)
    set_stage(ctx.run_id, key, "failed", error=message)
    repo.add_missing_input(ctx.run_id, key)


def _with_run_id(run_id: str, fn: PreStageFn, ctx: RunContext) -> PreStageResult:
    run_id_var.set(run_id)
    return fn(ctx)


# --------------------------------------------------------------------------- run


def run_analysis(run_id: str, engine: Engine, *, resume: bool = False) -> None:
    run_id_var.set(run_id)
    run = repo.get_run(run_id)
    ctx = RunContext(run.id, run.ticker, run.analysis_date, dict(run.settings or {}))
    repo.update_run(run_id, status="running", started_at=repo.utcnow(), error=None)
    events.publish(run_id, "run.started", {})

    try:
        todo = [k for k in PRE_STAGE_KEYS if repo.get_stage(run_id, k).status == "pending"]
        if todo:
            with ThreadPoolExecutor(max_workers=len(todo), thread_name_prefix="pre") as ex:
                list(ex.map(lambda k: _run_pre_stage(ctx, k), todo))

        evidence_block = evidence.render(run_id)

        def on_stage(key: str, status: str, **kw: Any) -> None:
            # The engine reports the Portfolio Manager finishing; the decision stage only
            # completes once the decision card below is saved.
            if key == "decision" and status == "done":
                return
            set_stage(run_id, key, status, **kw)

        result = engine.run(
            EngineContext(run=ctx, evidence_block=evidence_block, resume=resume, on_stage=on_stage)
        )
        _finish_decision(run_id, result)
    except StageFailed as exc:
        log.warning("run failed at %s: %s", exc.stage, exc.message)
        if repo.get_stage(run_id, exc.stage).status != "failed":
            set_stage(run_id, exc.stage, "failed", error=exc.message)
        _finish(run_id, "failed", f"{STAGE_BY_KEY[exc.stage].label} failed: {exc.message}")
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("run crashed")
        for st in repo.get_run_detail(run_id).stages:
            if st.status == "running":
                set_stage(run_id, st.key, "failed", error="Unexpected error")
        _finish(run_id, "failed", f"Unexpected error: {type(exc).__name__}")
        return
    _finish(run_id, "completed", None)


def _finish_decision(run_id: str, result: EngineResult) -> None:
    detail = repo.get_run_detail(run_id)
    card = decision_card.build(
        pm_text=result.pm_text,
        rating=result.rating,
        detail=detail,
        quick_llm=result.quick_llm,
    )
    repo.save_decision(run_id, card)
    events.publish(run_id, "decision.ready", card.model_dump(mode="json"))
    set_stage(run_id, "decision", "done", report_md=result.pm_text)


def _finish(run_id: str, status: str, error: str | None) -> None:
    repo.update_run(run_id, status=status, finished_at=repo.utcnow(), error=error)
    events.publish(run_id, "run.finished", {"status": status, "error": error})
