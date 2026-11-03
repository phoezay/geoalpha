"""`GeoAlphaTradingGraph`: TradingAgents extended by subclass, not forked (research R1, R2).

Two override points, both pinned by tests/contract/test_tradingagents_override_points.py:
- `create_run_state`: appends the GeoAlpha Evidence block to `instrument_context`, which
  every TradingAgents agent includes in its prompt.
- `run_with_events`: the upstream streaming loop with LangGraph `tasks` events kept, so
  node starts and finishes can drive per-stage progress.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tradingagents.agents.rating import run_rating
from tradingagents.dataflows.config import run_config, run_config_context
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

NodeEvent = Callable[[str, str, dict[str, Any] | None], None]
StateEvent = Callable[[dict[str, Any]], None]

ANALYSTS = ("market", "social", "news", "fundamentals")


def build_config(
    *,
    data_dir: Path,
    llm_provider: str,
    deep_model: str,
    quick_model: str,
    max_debate_rounds: int = 1,
) -> dict[str, Any]:
    config: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
    ta_dir = data_dir / "tradingagents"
    config.update(
        llm_provider=llm_provider,
        deep_think_llm=deep_model,
        quick_think_llm=quick_model,
        max_debate_rounds=max_debate_rounds,
        max_risk_discuss_rounds=1,
        checkpoint_enabled=True,
        results_dir=str(ta_dir / "logs"),
        data_cache_dir=str(ta_dir / "cache"),
        memory_log_path=str(ta_dir / "memory" / "trading_memory.md"),
    )
    return config


class GeoAlphaTradingGraph(TradingAgentsGraph):  # type: ignore[misc]
    def __init__(self, config: dict[str, Any], evidence_block: str = "") -> None:
        super().__init__(selected_analysts=ANALYSTS, debug=False, config=config)
        self.evidence_block = evidence_block

    def create_run_state(
        self, company_name: str, trade_date: str, asset_type: str = "stock", portfolio: Any = None
    ) -> dict[str, Any]:
        state: dict[str, Any] = dict(
            super().create_run_state(company_name, trade_date, asset_type, portfolio)
        )
        if self.evidence_block:
            state["instrument_context"] = f"{state['instrument_context']}\n{self.evidence_block}"
        return state

    def run_with_events(
        self, ticker: str, trade_date: str, on_node: NodeEvent, on_state: StateEvent
    ) -> tuple[dict[str, Any], str]:
        """Run the graph, reporting each top-level node start/finish. Mirrors upstream
        `propagate` -> `_run_graph`, including checkpoint resume and the decision log."""
        with run_config(self.config), self.checkpoint_scope(ticker, trade_date) as thread:
            init_state = self.create_run_state(ticker, trade_date)
            args = self.propagator.get_graph_args()
            args["stream_mode"] = ["tasks", "values"]
            if thread is not None:
                args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = thread
            graph_input = self.checkpoint_input(init_state)

            final_state: dict[str, Any] = dict(init_state)
            context = run_config_context(self.config)
            stream = context.run(self.graph.stream, graph_input, **args)
            try:
                while (step := context.run(next, stream, None)) is not None:
                    mode, chunk = step
                    if mode == "values":
                        final_state.update(chunk)
                        on_state(chunk)
                    elif mode == "tasks":
                        name = chunk.get("name", "")
                        if "result" in chunk or "error" in chunk:
                            if chunk.get("error"):
                                raise RuntimeError(f"{name}: {chunk['error']}")
                            on_node(name, "finish", _as_dict(chunk.get("result")))
                        else:
                            on_node(name, "start", None)
            finally:
                context.run(stream.close)

            self.record_decision(ticker, trade_date, final_state)
            self.clear_checkpoint_on_success(ticker, trade_date)
            return final_state, str(run_rating(final_state))


def _as_dict(result: Any) -> dict[str, Any] | None:
    if isinstance(result, dict):
        return result
    if isinstance(result, list):  # LangGraph may report node writes as (channel, value) pairs
        out: dict[str, Any] = {}
        for item in result:
            if isinstance(item, tuple) and len(item) == 2:
                out[str(item[0])] = item[1]
        return out or None
    return None
