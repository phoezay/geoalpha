"""T035: decision card rules (FR-014, SC-004)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from geoalpha.agents import decision_card
from geoalpha.api import schemas


def _detail(**over: Any) -> schemas.RunDetail:
    base: dict[str, Any] = dict(
        id="r1",
        ticker="XOM",
        requested_date=date(2026, 10, 30),
        analysis_date=date(2026, 10, 30),
        status="running",
        created_at=datetime.now(UTC),
        stages=[],
        settings={},
        llm_provider="x",
        deep_model="d",
        quick_model="q",
        missing_inputs=[],
        last_event_seq=0,
    )
    base.update(over)
    return schemas.RunDetail(**base)


def _card(**over: Any) -> schemas.Decision:
    base: dict[str, Any] = dict(
        rating="Buy",
        confidence="medium",
        summary="s",
        rationale_md="r",
        geo_statement="unavailable",
        cited_signal_ids=[],
        forecast_alignment="unavailable",
        missing_inputs=[],
    )
    base.update(over)
    return schemas.Decision(**base)


def test_cites_requires_ids() -> None:
    with pytest.raises(decision_card.InvalidDecisionCard):
        decision_card.validate(_card(geo_statement="cites"))


def test_ids_require_cites() -> None:
    with pytest.raises(decision_card.InvalidDecisionCard):
        decision_card.validate(_card(geo_statement="none_material", cited_signal_ids=["r1:1"]))


def test_high_confidence_capped_when_inputs_missing() -> None:
    with pytest.raises(decision_card.InvalidDecisionCard):
        decision_card.validate(_card(confidence="high", missing_inputs=["geo"]))


class _FakeStructured:
    def __init__(self, out: Any) -> None:
        self.out = out

    def invoke(self, _prompt: str) -> Any:
        return self.out


class _FakeLLM:
    def __init__(self, out: Any) -> None:
        self.out = out

    def with_structured_output(self, _model: Any) -> _FakeStructured:
        return _FakeStructured(self.out)


def test_geo_skipped_means_unavailable() -> None:
    card = decision_card.build(
        pm_text="**Rating**: Overweight\n\nGood.", rating="Overweight", detail=_detail()
    )
    assert card.geo_statement == "unavailable" and card.cited_signal_ids == []
    assert card.forecast_alignment == "unavailable"
    assert card.rating == "Overweight"


def test_llm_high_confidence_capped_to_medium_when_missing() -> None:
    llm = _FakeLLM(
        decision_card._CardLLM(confidence="high", summary="Strong.", cited_signal_ids=[])
    )
    card = decision_card.build(
        pm_text="Buy it.", rating="Buy", detail=_detail(missing_inputs=["geo"]), quick_llm=llm
    )
    assert card.confidence == "medium"
    assert card.missing_inputs == ["geo"]


def test_review_rating_falls_back_to_hold_with_low_confidence() -> None:
    card = decision_card.build(pm_text="No clear call.", rating="REVIEW", detail=_detail())
    assert card.rating == "Hold" and card.confidence == "low"


def test_material_geo_without_llm_citations_cites_top_signals() -> None:
    signal = schemas.GeoSignal(
        id="r1:1",
        rank=1,
        region="SA",
        category="energy",
        severity=4,
        impact_direction="positive",
        headline="h",
        rationale="r",
        valid_at=datetime.now(UTC),
        source_label="WorldMonitor",
    )
    geo = schemas.GeoSummary(materiality="material", signals=[signal])
    card = decision_card.build(pm_text="Buy.", rating="Buy", detail=_detail(geo=geo))
    assert card.geo_statement == "cites" and card.cited_signal_ids == ["r1:1"]


def test_forecast_alignment() -> None:
    fc = schemas.PriceForecast(
        model="m",
        history=[],
        path=[],
        horizon=5,
        sample_count=30,
        last_close=100,
        expected_move_pct=2.0,
        range_low=95,
        range_high=105,
    )
    assert decision_card.forecast_alignment("Buy", fc) == "supports"
    assert decision_card.forecast_alignment("Sell", fc) == "contradicts"
    assert decision_card.forecast_alignment("Hold", fc) == "neutral"
