"""T032: the upstream hooks GeoAlphaTradingGraph relies on still exist (research R1/R2).
If this fails after an upgrade, re-verify agents/graph.py against the new upstream."""

from __future__ import annotations

import inspect

import tradingagents
from tradingagents.graph.trading_graph import TradingAgentsGraph


def test_pinned_version() -> None:
    assert tradingagents.__version__ == "0.7.1"


def test_override_points_exist() -> None:
    for name in (
        "create_run_state",
        "resolve_instrument_context",
        "record_decision",
        "checkpoint_scope",
        "checkpoint_input",
        "clear_checkpoint_on_success",
    ):
        assert callable(getattr(TradingAgentsGraph, name, None)), name
    params = inspect.signature(TradingAgentsGraph.create_run_state).parameters
    assert list(params)[:3] == ["self", "company_name", "trade_date"]


def test_run_config_context_available() -> None:
    from tradingagents.dataflows.config import run_config, run_config_context

    assert callable(run_config) and callable(run_config_context)


def test_instrument_context_reaches_every_agent() -> None:
    """Every agent prompt builder reads instrument_context, so the evidence block
    appended to it reaches the whole committee."""
    from tradingagents.agents.state import AgentState

    assert "instrument_context" in AgentState.__annotations__
    import tradingagents.agents.managers.portfolio_manager as pm
    import tradingagents.agents.researchers.bear_researcher as bear
    import tradingagents.agents.researchers.bull_researcher as bull
    import tradingagents.agents.trader.trader as trader

    for module in (bull, bear, trader, pm):
        assert "instrument_context" in inspect.getsource(module), module.__name__


def test_node_names_match_stage_map() -> None:
    from tradingagents.graph import setup

    from geoalpha.agents.stage_map import NODE_TO_STAGE

    source = inspect.getsource(setup)
    for node in NODE_TO_STAGE:
        if node.endswith("Analyst") and node.split()[0] in (
            "Market",
            "Sentiment",
            "News",
            "Fundamentals",
        ):
            continue  # registered through ANALYST_NODE_SPECS
        assert f'"{node}"' in source, node
    from tradingagents.graph.analyst_execution import ANALYST_NODE_SPECS

    assert {s.agent_node for s in ANALYST_NODE_SPECS.values()} == {
        "Market Analyst",
        "Sentiment Analyst",
        "News Analyst",
        "Fundamentals Analyst",
    }
