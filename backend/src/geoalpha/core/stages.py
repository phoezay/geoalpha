"""The 10 fixed stages of a run (data-model.md, *Stage keys*)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

StageKey = Literal[
    "geo",
    "forecast",
    "market",
    "sentiment",
    "news",
    "fundamentals",
    "research_debate",
    "trader",
    "risk_debate",
    "decision",
]
StageStatus = Literal["pending", "running", "done", "failed", "unavailable", "skipped"]
RunStatus = Literal["queued", "running", "completed", "failed", "interrupted"]
Rating = Literal["Buy", "Overweight", "Hold", "Underweight", "Sell"]

STAGE_KEYS: tuple[StageKey, ...] = get_args(StageKey)
RATING_CHOICES: tuple[str, ...] = get_args(Rating)
PRE_STAGE_KEYS: tuple[StageKey, ...] = ("geo", "forecast")
TA_STAGE_KEYS: tuple[StageKey, ...] = tuple(k for k in STAGE_KEYS if k not in PRE_STAGE_KEYS)
TERMINAL_STAGE: frozenset[str] = frozenset({"done", "failed", "unavailable", "skipped"})
TERMINAL_RUN: frozenset[str] = frozenset({"completed", "failed", "interrupted"})


@dataclass(frozen=True)
class StageDef:
    key: StageKey
    label: str
    critical: bool
    timeout_s: int


STAGE_DEFS: tuple[StageDef, ...] = (
    StageDef("geo", "Geopolitical Analyst", False, 120),
    StageDef("forecast", "Price Forecast", False, 180),
    StageDef("market", "Market Analyst", True, 600),
    StageDef("sentiment", "Sentiment Analyst", True, 600),
    StageDef("news", "News Analyst", True, 600),
    StageDef("fundamentals", "Fundamentals Analyst", True, 600),
    StageDef("research_debate", "Bull vs Bear Debate", True, 600),
    StageDef("trader", "Trader", True, 600),
    StageDef("risk_debate", "Risk Review", True, 600),
    StageDef("decision", "Final Decision", True, 600),
)
STAGE_BY_KEY: dict[str, StageDef] = {d.key: d for d in STAGE_DEFS}
