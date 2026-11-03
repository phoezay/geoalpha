"""Geopolitical Analyst stage (research R5): exposure -> sourced data -> ranked signals.

Two assessors share one contract:
- `deterministic_assess` (fixture/demo mode, offline, reproducible)
- `llm_assess` (real mode, quick-tier model with structured output)
Both may only emit signals that point at a fetched snapshot. Unsourced signals are dropped.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, Field

from geoalpha.api import schemas
from geoalpha.core import market_calendar
from geoalpha.geo.exposure import ExposureProfile
from geoalpha.geo.fixture import SOURCE_LABEL as FIXTURE_LABEL
from geoalpha.geo.fixture import SOURCE_URL as FIXTURE_URL
from geoalpha.geo.provider import Fetched, SnapshottingProvider

log = logging.getLogger(__name__)

MAX_SIGNALS = 10
MATERIAL_SEVERITY = 3
_CATEGORIES = {
    "conflict",
    "instability",
    "sanctions",
    "supply_route",
    "commodity_shock",
    "energy",
    "cyber",
    "disaster",
    "policy",
    "other",
}


@dataclass
class Draft:
    """A signal before ranking. `fetched` is the snapshot it came from."""

    region: str
    category: str
    severity: int
    impact: str
    headline: str
    rationale: str
    valid_at: datetime
    fetched: Fetched


# ------------------------------------------------------------------ collection


def collect(provider: SnapshottingProvider, exposure: ExposureProfile) -> list[Fetched]:
    calls: list[tuple[str, dict[str, Any]]] = [("get_world_brief", {})]
    for c in exposure.countries:
        calls += [
            ("get_country_risk", {"country_code": c.iso2}),
            ("get_conflict_events", {"country": c.iso2, "limit": 10}),
            ("get_sanctions_data", {"country": c.iso2}),
        ]
        if exposure.chokepoints:
            calls.append(("get_maritime_activity", {"country_code": c.iso2}))
    return [provider.fetch(tool, params) for tool, params in calls]


def _item_time(item: dict[str, Any], fetched: Fetched) -> datetime:
    raw = item.get("date") or item.get("timestamp")
    if raw:
        try:
            d = date.fromisoformat(str(raw)[:10])
            return datetime.combine(d, time(12), tzinfo=market_calendar.ET).astimezone(UTC)
        except ValueError:
            pass
    return fetched.captured_at


def _after(dt: datetime, analysis_date: date) -> bool:
    return dt.astimezone(market_calendar.ET).date() > analysis_date


# ------------------------------------------------------------------ deterministic


def deterministic_assess(
    fetched: list[Fetched], exposure: ExposureProfile, ticker: str, analysis_date: date
) -> list[Draft]:
    weights = {c.iso2: c for c in exposure.countries}
    drafts: list[Draft] = []

    def add(f: Fetched, cc: str, cat: str, sev: int, headline: str, item: dict[str, Any]) -> None:
        when = _item_time(item, f)
        if _after(when, analysis_date):  # an item dated after the analysis date is never used
            return
        country = weights.get(cc)
        impact = exposure.impact.get(cat, "uncertain")
        reason = country.reason if country else "Listed exposure"
        drafts.append(
            Draft(
                region=cc,
                category=cat if cat in _CATEGORIES else "other",
                severity=max(1, min(5, sev)),
                impact=impact,
                headline=headline[:140],
                rationale=f"{ticker} exposure: {reason.lower()}. Escalation here is typically "
                f"{impact} for the stock.",
                valid_at=when,
                fetched=f,
            )
        )

    for f in fetched:
        cc = str(f.params.get("country_code") or f.params.get("country") or "")
        p = f.payload if isinstance(f.payload, dict) else {}
        if f.tool == "get_country_risk" and isinstance(p.get("cii_score"), int | float):
            score = float(p["cii_score"])
            if score >= 60:
                sev = 3 if score < 70 else 4 if score < 80 else 5
                add(
                    f,
                    cc,
                    "instability",
                    sev,
                    f"{cc} instability index at {score:.0f} ({p.get('band', 'n/a')})",
                    p,
                )
        elif f.tool == "get_conflict_events":
            for ev in p.get("events", []):
                add(
                    f,
                    cc,
                    str(ev.get("category", "conflict")),
                    int(ev.get("severity", 3)),
                    str(ev.get("title", "Conflict event")),
                    ev,
                )
        elif f.tool == "get_sanctions_data":
            for s in p.get("designations", []):
                add(
                    f,
                    cc,
                    "sanctions",
                    int(s.get("severity", 3)),
                    str(s.get("title", "Sanctions")),
                    s,
                )
        elif f.tool == "get_maritime_activity":
            for d in p.get("disruptions", []):
                add(
                    f,
                    cc,
                    "supply_route",
                    int(d.get("severity", 3)),
                    str(d.get("title", "Shipping disruption")),
                    d,
                )

    def relevance(d: Draft) -> float:
        w = weights[d.region].weight if d.region in weights else 0.1
        return d.severity * (0.5 + w)

    return sorted(drafts, key=relevance, reverse=True)


# ------------------------------------------------------------------ LLM


class _LLMSignal(BaseModel):
    source_ref: str = Field(description="The [S#] tag of the payload this signal comes from")
    region: str
    category: Literal[
        "conflict",
        "instability",
        "sanctions",
        "supply_route",
        "commodity_shock",
        "energy",
        "cyber",
        "disaster",
        "policy",
        "other",
    ]
    severity: int = Field(ge=1, le=5)
    impact_direction: Literal["positive", "negative", "mixed", "uncertain"]
    headline: str = Field(max_length=140)
    rationale: str


class _LLMAssessment(BaseModel):
    signals: list[_LLMSignal] = Field(default_factory=list, max_length=MAX_SIGNALS)


def llm_assess(
    llm: Any, fetched: list[Fetched], exposure: ExposureProfile, ticker: str, analysis_date: date
) -> list[Draft]:
    tagged = {f"S{i + 1}": f for i, f in enumerate(fetched)}
    blocks = []
    for tag, f in tagged.items():
        body = json.dumps(f.payload, ensure_ascii=False, default=str)[:2500]
        blocks.append(f"[{tag}] {f.tool} {json.dumps(f.params)}\n{body}")
    prompt = (
        f"You are the Geopolitical Analyst on a trading committee assessing {ticker} as of "
        f"{analysis_date.isoformat()}.\n\nExposure profile:\n{exposure.model_dump_json()}\n\n"
        "Source payloads (only use these; ignore anything dated after the analysis date):\n\n"
        + "\n\n".join(blocks)
        + "\n\nReturn up to 10 signals that materially matter for this stock, most relevant "
        "first. Every signal MUST cite the [S#] tag it came from. Return no signals if nothing "
        "is material."
    )
    out = llm.with_structured_output(_LLMAssessment).invoke(prompt)
    result = out if isinstance(out, _LLMAssessment) else _LLMAssessment.model_validate(out)
    drafts = []
    for s in result.signals:
        src = tagged.get(s.source_ref.strip("[] "))
        if src is None:
            continue  # unsourced: dropped (Constitution II)
        drafts.append(
            Draft(
                region=s.region,
                category=s.category,
                severity=s.severity,
                impact=s.impact_direction,
                headline=s.headline,
                rationale=s.rationale,
                valid_at=src.captured_at,
                fetched=src,
            )
        )
    return drafts


# ------------------------------------------------------------------ ranking


def finalize(
    run_id: str, drafts: list[Draft], fixture: bool
) -> list[tuple[schemas.GeoSignal, str]]:
    """Rank 1..n (max 10), clamp severity, attach ids and attribution.
    Returns (signal, snapshot_id) pairs."""
    signals: list[Any] = []
    for rank, d in enumerate(drafts[:MAX_SIGNALS], start=1):
        signals.append(
            schemas.GeoSignal(
                id=f"{run_id}:{rank}",
                rank=rank,
                region=d.region,
                category=d.category if d.category in _CATEGORIES else "other",
                severity=max(1, min(5, d.severity)),
                impact_direction=d.impact
                if d.impact in ("positive", "negative", "mixed", "uncertain")
                else "uncertain",
                headline=d.headline[:140],
                rationale=d.rationale,
                valid_at=d.valid_at,
                source_label=(FIXTURE_LABEL if fixture else "WorldMonitor")
                + f" · {d.fetched.tool}",
                source_url=FIXTURE_URL if fixture else "https://www.worldmonitor.app",
            )
        )
        signals[-1] = (signals[-1], d.fetched.snapshot_id)
    return signals


def materiality(signals: list[schemas.GeoSignal]) -> str:
    return "material" if any(s.severity >= MATERIAL_SEVERITY for s in signals) else "immaterial"
