"""Final decision card: confidence, plain-language summary, evidence citations (research R7).

TradingAgents' PortfolioDecision has a rating but no confidence, and nothing forces it to
cite the geopolitical evidence. This step adds both and enforces the SC-004 rule.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field

from geoalpha.api import schemas
from geoalpha.core.stages import Rating

log = logging.getLogger(__name__)

RATINGS: tuple[str, ...] = get_args(Rating)
_BULLISH = {"Buy", "Overweight"}
_BEARISH = {"Sell", "Underweight"}
_MOVE_THRESHOLD_PCT = 0.5


class InvalidDecisionCard(ValueError):
    pass


class _CardLLM(BaseModel):
    """What the quick-tier model is asked for."""

    confidence: Literal["low", "medium", "high"] = Field(
        description="How strongly the evidence supports the rating."
    )
    summary: str = Field(
        description="2-3 plain-language sentences for a non-specialist explaining the rating "
        "and its main reasons. Max 600 characters."
    )
    cited_signal_ids: list[str] = Field(
        default_factory=list,
        description="Ids of the geopolitical signals that materially influenced the decision.",
    )


def validate(card: schemas.Decision, signal_ids: set[str] | None = None) -> None:
    """SC-004: a decision cites signals, or says why it doesn't. Never both, never neither."""
    if card.geo_statement == "cites" and not card.cited_signal_ids:
        raise InvalidDecisionCard("geo_statement 'cites' requires cited_signal_ids")
    if card.geo_statement != "cites" and card.cited_signal_ids:
        raise InvalidDecisionCard("cited_signal_ids requires geo_statement 'cites'")
    if signal_ids is not None and not set(card.cited_signal_ids) <= signal_ids:
        raise InvalidDecisionCard("cited_signal_ids must reference this run's signals")
    if card.missing_inputs and card.confidence == "high":
        raise InvalidDecisionCard("confidence must be capped at medium when inputs are missing")


def normalize_rating(raw: str, pm_text: str) -> tuple[str, bool]:
    """(rating, was_parsed). TradingAgents may return REVIEW when the PM gave no rating."""
    if raw in RATINGS:
        return raw, True
    m = re.search(r"\b(Buy|Overweight|Hold|Underweight|Sell)\b", pm_text)
    if m:
        return m.group(1), True
    return "Hold", False


def forecast_alignment(rating: str, forecast: schemas.PriceForecast | None) -> str:
    if forecast is None:
        return "unavailable"
    move = forecast.expected_move_pct
    if abs(move) < _MOVE_THRESHOLD_PCT:
        return "neutral"
    up = move > 0
    if (rating in _BULLISH and up) or (rating in _BEARISH and not up):
        return "supports"
    if rating in _BULLISH or rating in _BEARISH:
        return "contradicts"
    return "neutral"


def _plain_summary(pm_text: str) -> str:
    # Drop bold section labels ("**Executive summary.**") before stripping markdown.
    text = re.sub(r"\*\*[^*\n]{1,40}[.:]\*\*\s*", "", pm_text)
    text = re.sub(r"[#*_>`|]", "", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not re.match(r"^(Rating|Final|Decision)\s*:", ln, re.I)]
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(lines))
    out = ""
    for s in sentences:
        if len(out) + len(s) + 1 > 600:
            break
        out = f"{out} {s}".strip()
        if len(out) > 280:
            break
    return out or "The portfolio manager did not provide a summary."


def build(
    *,
    pm_text: str,
    rating: str,
    detail: schemas.RunDetail,
    quick_llm: Any | None = None,
) -> schemas.Decision:
    rating, parsed = normalize_rating(rating, pm_text)
    missing = [k for k in detail.missing_inputs if k in ("geo", "forecast")]
    geo = detail.geo
    signals = {s.id: s for s in (geo.signals if geo else [])}
    alignment = forecast_alignment(rating, detail.forecast)

    confidence: str = "low" if alignment == "contradicts" or not parsed else "medium"
    summary = _plain_summary(pm_text)
    cited: list[str] = []

    if quick_llm is not None and parsed:
        try:
            out = _ask_llm(quick_llm, pm_text, rating, geo, detail.forecast, alignment)
            confidence, summary = out.confidence, out.summary[:600]
            cited = [i for i in out.cited_signal_ids if i in signals]
        except Exception:  # noqa: BLE001 - the deterministic card is a safe fallback
            log.exception("decision card LLM step failed; using deterministic card")

    if geo is None or geo.materiality == "unavailable":
        geo_statement, cited = "unavailable", []
    elif geo.materiality == "immaterial" or not signals:
        geo_statement, cited = "none_material", []
    else:
        if not cited:  # material exposure must be cited: fall back to the top-ranked signals
            cited = [s.id for s in sorted(signals.values(), key=lambda s: s.rank)[:3]]
        geo_statement = "cites"

    if missing and confidence == "high":
        confidence = "medium"
    if not parsed:
        summary = "The portfolio manager gave no clear rating; shown as Hold for review. " + summary

    card = schemas.Decision(
        rating=rating,
        confidence=confidence,
        summary=summary[:600],
        rationale_md=pm_text,
        geo_statement=geo_statement,
        cited_signal_ids=cited,
        forecast_alignment=alignment,
        missing_inputs=missing,
    )
    validate(card, set(signals))
    return card


def _ask_llm(
    llm: Any,
    pm_text: str,
    rating: str,
    geo: schemas.GeoSummary | None,
    forecast: schemas.PriceForecast | None,
    alignment: str,
) -> _CardLLM:
    geo_lines = (
        "\n".join(
            f"[{s.id}] {s.region} {s.category} severity {s.severity} {s.impact_direction}: "
            f"{s.headline}"
            for s in geo.signals
        )
        if geo and geo.signals
        else "No geopolitical signals available."
    )
    fc = (
        f"Expected move {forecast.expected_move_pct:+.1f}% over {forecast.horizon} sessions "
        f"(p10-p90 {forecast.range_low:.2f}-{forecast.range_high:.2f}); {alignment} the rating."
        if forecast
        else "No price forecast available."
    )
    prompt = (
        "You summarise a trading committee's final decision for a research dashboard.\n"
        f"Final rating: {rating}\n\nPortfolio manager decision:\n{pm_text}\n\n"
        f"Geopolitical signals:\n{geo_lines}\n\nPrice model: {fc}\n\n"
        "Return the confidence, a short plain-language summary, and the ids of any "
        "geopolitical signals that materially influenced the decision (only ids listed above)."
    )
    structured = llm.with_structured_output(_CardLLM)
    result = structured.invoke(prompt)
    if not isinstance(result, _CardLLM):
        result = _CardLLM.model_validate(result)
    return result
