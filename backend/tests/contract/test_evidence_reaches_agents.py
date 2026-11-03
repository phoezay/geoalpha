"""T069: the GeoAlpha Evidence block reaches the Bull, Bear, Trader and Portfolio Manager
prompts through the `instrument_context` override (research R1). No network, no LLM."""

from __future__ import annotations

from typing import Any

import pytest
from tradingagents.agents import (
    create_bear_researcher,
    create_bull_researcher,
    create_portfolio_manager,
    create_trader,
)
from tradingagents.graph.propagation import Propagator

from geoalpha.agents.graph import GeoAlphaTradingGraph

SENTINEL = "### GeoAlpha Evidence\n- SENTINEL-7f3a signal [r:1]\n### End of GeoAlpha Evidence"


class _Stop(Exception):
    pass


class CapturingLLM:
    """Records every prompt, then aborts the node (only what it was asked matters)."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def invoke(self, prompt: Any, *a: Any, **k: Any) -> Any:
        self.prompts.append(str(prompt))
        raise _Stop

    def with_structured_output(self, *a: Any, **k: Any) -> CapturingLLM:
        return self

    def bind_tools(self, *a: Any, **k: Any) -> CapturingLLM:
        return self


@pytest.fixture
def state() -> dict[str, Any]:
    graph = object.__new__(GeoAlphaTradingGraph)
    graph.propagator = Propagator(max_recur_limit=100)
    graph.evidence_block = SENTINEL
    graph.resolve_instrument_context = lambda *a, **k: "Instrument: XOM (Exxon Mobil)"
    st = GeoAlphaTradingGraph.create_run_state(graph, "XOM", "2026-10-30")
    st.update(
        market_report="m",
        sentiment_report="s",
        news_report="n",
        fundamentals_report="f",
        investment_plan="plan",
        trader_investment_plan="trade",
        past_context="",
    )
    return st


def test_override_appends_evidence(state: dict[str, Any]) -> None:
    assert state["instrument_context"].startswith("Instrument: XOM")
    assert SENTINEL in state["instrument_context"]


@pytest.mark.parametrize(
    "factory",
    [create_bull_researcher, create_bear_researcher, create_trader, create_portfolio_manager],
)
def test_evidence_in_agent_prompt(factory: Any, state: dict[str, Any]) -> None:
    llm = CapturingLLM()
    node = factory(llm)
    try:
        node(state)
    except Exception:  # noqa: BLE001 - the capturing LLM aborts every call
        pass
    assert llm.prompts, f"{factory.__name__} never called the model"
    assert any("SENTINEL-7f3a" in p for p in llm.prompts), factory.__name__
