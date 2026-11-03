"""T068: signal ranking, attribution and materiality."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from geoalpha.geo import analyst
from geoalpha.geo.exposure import ExposureCountry, ExposureProfile, get_exposure
from geoalpha.geo.fixture import FixtureGeoSource
from geoalpha.geo.provider import Fetched

AD = date(2026, 11, 2)


def _fetched(tool: str, params: dict[str, Any], payload: Any, sid: str = "snap1") -> Fetched:
    return Fetched(sid, payload, datetime(2026, 11, 2, 15, tzinfo=UTC), tool, params)


def _all(ticker: str) -> tuple[list[Fetched], ExposureProfile]:
    exp = get_exposure(ticker, AD, fixture=True)
    src = FixtureGeoSource()
    calls: list[tuple[str, dict[str, Any]]] = [("get_world_brief", {})]
    for c in exp.countries:
        calls += [
            ("get_country_risk", {"country_code": c.iso2}),
            ("get_conflict_events", {"country": c.iso2, "limit": 10}),
            ("get_sanctions_data", {"country": c.iso2}),
        ]
        if exp.chokepoints:
            calls.append(("get_maritime_activity", {"country_code": c.iso2}))
    return [_fetched(t, p, src.call(t, p), f"s{i}") for i, (t, p) in enumerate(calls)], exp


def _signals(ticker: str) -> list[Any]:
    fetched, exp = _all(ticker)
    pairs = analyst.finalize("r1", analyst.deterministic_assess(fetched, exp, ticker, AD), True)
    return pairs


def test_xom_is_material_ranked_and_sourced() -> None:
    pairs = _signals("XOM")
    signals = [s for s, _ in pairs]
    assert 1 <= len(signals) <= 10
    assert [s.rank for s in signals] == list(range(1, len(signals) + 1))
    assert all(sid for _, sid in pairs), "every signal keeps its snapshot id"
    assert all(1 <= s.severity <= 5 and s.source_label for s in signals)
    assert analyst.materiality(signals) == "material"


def test_ko_is_immaterial() -> None:
    signals = [s for s, _ in _signals("KO")]
    assert analyst.materiality(signals) == "immaterial"


def test_items_dated_after_analysis_date_are_dropped() -> None:
    exp = ExposureProfile(countries=[ExposureCountry(iso2="SA", weight=0.5, reason="r")])
    payload = {
        "events": [
            {"title": "before", "severity": 4, "date": "2026-10-30"},
            {"title": "after", "severity": 5, "date": "2026-11-05"},
        ]
    }
    drafts = analyst.deterministic_assess(
        [_fetched("get_conflict_events", {"country": "SA"}, payload)], exp, "XOM", AD
    )
    assert [d.headline for d in drafts] == ["before"]


def test_severity_clamped_and_max_ten() -> None:
    exp = ExposureProfile(countries=[ExposureCountry(iso2="SA", weight=0.5, reason="r")])
    events = [{"title": f"e{i}", "severity": 9, "date": "2026-10-01"} for i in range(15)]
    drafts = analyst.deterministic_assess(
        [_fetched("get_conflict_events", {"country": "SA"}, {"events": events})], exp, "XOM", AD
    )
    signals = [s for s, _ in analyst.finalize("r1", drafts, fixture=True)]
    assert len(signals) == 10 and all(s.severity == 5 for s in signals)


class _FakeLLM:
    def __init__(self, out: Any) -> None:
        self.out = out

    def with_structured_output(self, _m: Any) -> _FakeLLM:
        return self

    def invoke(self, _p: Any) -> Any:
        return self.out


def test_llm_signals_without_known_source_are_dropped() -> None:
    fetched = [_fetched("get_country_risk", {"country_code": "SA"}, {"cii_score": 70})]
    common = dict(region="SA", category="energy", severity=4, impact_direction="positive")
    out = analyst._LLMAssessment(
        signals=[
            analyst._LLMSignal(source_ref="[S1]", headline="ok", rationale="r", **common),
            analyst._LLMSignal(source_ref="[S9]", headline="unsourced", rationale="r", **common),
        ]
    )
    exp = ExposureProfile(countries=[ExposureCountry(iso2="SA", weight=1, reason="r")])
    drafts = analyst.llm_assess(_FakeLLM(out), fetched, exp, "XOM", AD)
    assert [d.headline for d in drafts] == ["ok"]
    assert drafts[0].fetched.snapshot_id == "snap1"
