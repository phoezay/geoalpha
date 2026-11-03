"""LangGraph node names (TradingAgents v0.7.1) -> GeoAlpha stage keys (data-model.md)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

NODE_TO_STAGE: dict[str, str] = {
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

# Debates loop between their nodes for a configurable number of rounds, so a multi-node
# stage is only known to be over when the stage after it starts.
_FOLLOWING_STAGE = {"trader": "research_debate", "decision": "risk_debate"}
_SINGLE_NODE = {"market", "sentiment", "news", "fundamentals", "trader"}

ReportFn = Callable[[str, dict[str, Any]], tuple[str | None, dict[str, Any] | None]]
EmitFn = Callable[..., None]


def stage_report(stage: str, state: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    """(report_md, payload) for a stage from the graph state."""
    match stage:
        case "market":
            return state.get("market_report") or None, None
        case "sentiment":
            return state.get("sentiment_report") or None, None
        case "news":
            return state.get("news_report") or None, None
        case "fundamentals":
            return state.get("fundamentals_report") or None, None
        case "research_debate":
            debate = state.get("investment_debate_state") or {}
            plan = state.get("investment_plan") or None
            return plan, {
                "bull_history": debate.get("bull_history", ""),
                "bear_history": debate.get("bear_history", ""),
                "judge": plan or "",
            }
        case "trader":
            return state.get("trader_investment_plan") or None, None
        case "risk_debate":
            risk = state.get("risk_debate_state") or {}
            return None, {
                "aggressive": risk.get("aggressive_history", ""),
                "conservative": risk.get("conservative_history", ""),
                "neutral": risk.get("neutral_history", ""),
            }
        case "decision":
            return state.get("final_trade_decision") or None, None
    return None, None


class StageTracker:
    """Turns node start/finish events into stage-level running/done transitions."""

    def __init__(self, emit: EmitFn, already_done: set[str] | None = None) -> None:
        self.emit = emit
        self.state: dict[str, Any] = {}
        self.started: set[str] = set(already_done or ())
        self.finished: set[str] = set(already_done or ())

    def update_state(self, values: dict[str, Any]) -> None:
        self.state.update(values)

    def node_started(self, node: str) -> None:
        stage = NODE_TO_STAGE.get(node)
        if stage is None:
            return
        if (prev := _FOLLOWING_STAGE.get(stage)) is not None:
            self._finish(prev)
        if stage not in self.started:
            self.started.add(stage)
            self.emit(stage, "running")

    def node_finished(self, node: str, result: dict[str, Any] | None) -> None:
        stage = NODE_TO_STAGE.get(node)
        if result:
            self.state.update({k: v for k, v in result.items() if k != "messages"})
        if stage in _SINGLE_NODE:
            self._finish(stage)

    def finish_all(self) -> None:
        for stage in ("research_debate", "risk_debate", "decision"):
            if stage in self.started:
                self._finish(stage)

    def _finish(self, stage: str) -> None:
        if stage in self.finished:
            return
        if stage not in self.started:  # e.g. resumed past it
            self.started.add(stage)
            self.emit(stage, "running")
        self.finished.add(stage)
        report_md, payload = stage_report(stage, self.state)
        self.emit(stage, "done", report_md=report_md, payload=payload)

    def running(self) -> list[str]:
        return sorted(self.started - self.finished)
