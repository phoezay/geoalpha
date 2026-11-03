"""T033: node -> stage mapping and stage-level transitions."""

from __future__ import annotations

from typing import Any

from geoalpha.agents.stage_map import NODE_TO_STAGE, StageTracker


def test_mapping_matches_data_model() -> None:
    assert NODE_TO_STAGE == {
        "Market Analyst": "market",
        "Sentiment Analyst": "sentiment",
        "News Analyst": "news",
        "Fundamentals Analyst": "fundamentals",
        "Bull Researcher": "research_debate",
        "Bear Researcher": "research_debate",
        "Research Manager": "research_debate",
        "Trader": "trader",
        "Aggressive Analyst": "risk_debate",
        "Conservative Analyst": "risk_debate",
        "Neutral Analyst": "risk_debate",
        "Portfolio Manager": "decision",
    }


def _tracker() -> tuple[StageTracker, list[tuple[str, str, dict[str, Any]]]]:
    log: list[tuple[str, str, dict[str, Any]]] = []
    return StageTracker(lambda s, st, **kw: log.append((s, st, kw))), log


def test_multi_node_stage_completes_only_after_last_node() -> None:
    t, log = _tracker()
    for node in ("Bull Researcher", "Bear Researcher", "Bull Researcher", "Bear Researcher"):
        t.node_started(node)
        t.node_finished(node, None)
    t.node_started("Research Manager")
    t.update_state(
        {
            "investment_plan": "Overweight plan",
            "investment_debate_state": {"bull_history": "b", "bear_history": "x"},
        }
    )
    t.node_finished("Research Manager", None)
    assert ("research_debate", "running", {}) in log
    assert not any(s == "research_debate" and st == "done" for s, st, _ in log)
    t.node_started("Trader")
    done = [kw for s, st, kw in log if s == "research_debate" and st == "done"]
    assert done == [
        {
            "report_md": "Overweight plan",
            "payload": {"bull_history": "b", "bear_history": "x", "judge": "Overweight plan"},
        }
    ]


def test_single_node_stage_done_on_finish_with_report() -> None:
    t, log = _tracker()
    t.node_started("Market Analyst")
    t.node_finished("Market Analyst", {"market_report": "## Market"})
    assert log == [
        ("market", "running", {}),
        ("market", "done", {"report_md": "## Market", "payload": None}),
    ]


def test_unknown_nodes_ignored_and_finish_all() -> None:
    t, log = _tracker()
    t.node_started("Memory Log")
    t.node_started("Aggressive Analyst")
    t.node_started("Portfolio Manager")
    t.update_state({"final_trade_decision": "**Rating**: Buy"})
    t.finish_all()
    assert [(s, st) for s, st, _ in log] == [
        ("risk_debate", "running"),
        ("risk_debate", "done"),
        ("decision", "running"),
        ("decision", "done"),
    ]


def test_resume_skips_already_done_stages() -> None:
    log: list[tuple[str, str]] = []
    t = StageTracker(lambda s, st, **kw: log.append((s, st)), already_done={"market"})
    t.node_started("Market Analyst")
    t.node_finished("Market Analyst", {"market_report": "x"})
    assert log == []
