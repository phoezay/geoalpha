"""Pydantic models mirroring contracts/openapi.yaml (kept in sync by the contract test)."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from geoalpha.core.stages import Rating, RunStatus, StageKey, StageStatus

DISCLAIMER = "Research output, not financial advice."

GeoCategory = Literal[
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


class _Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Problem(_Model):
    type: str | None = None
    title: str
    status: int
    detail: str | None = None
    field_errors: dict[str, str] | None = None


class Health(_Model):
    ok: bool
    llm_configured: bool
    llm_provider: str | None = None
    geo_provider: Literal["worldmonitor", "snapshot", "fixture"]
    geo_configured: bool | None = None
    forecast_model_ready: bool
    problems: list[str] = []


class TickerValidation(_Model):
    ticker: str
    valid: bool
    name: str | None = None
    exchange: str | None = None
    reason: str | None = None


class RunCreate(_Model):
    ticker: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")
    date: dt.date | None = Field(None, description="Defaults to most recent completed NYSE session")


class RetryRequest(_Model):
    mode: Literal["resume", "fresh"] = "resume"


class Stage(_Model):
    key: StageKey
    label: str
    order: int
    critical: bool
    status: StageStatus
    started_at: dt.datetime | None = None
    finished_at: dt.datetime | None = None
    attempts: int
    report_md: str | None = None
    payload: dict[str, Any] | None = None
    error: str | None = None


class ExposureCountry(_Model):
    iso2: str
    weight: float
    reason: str


class Exposure(_Model):
    countries: list[ExposureCountry] = []
    commodities: list[str] = []
    chokepoints: list[str] = []


class GeoSignal(_Model):
    id: str
    rank: int = Field(ge=1, le=10)
    region: str
    category: GeoCategory
    severity: int = Field(ge=1, le=5)
    impact_direction: Literal["positive", "negative", "mixed", "uncertain"]
    headline: str = Field(max_length=140)
    rationale: str
    valid_at: dt.datetime
    source_label: str
    source_url: str | None = None


class GeoSummary(_Model):
    materiality: Literal["material", "immaterial", "unavailable"]
    unavailable_reason: str | None = None
    exposure: Exposure | None = None
    signals: list[GeoSignal] = []


class Bar(_Model):
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class ForecastPoint(_Model):
    date: dt.date
    p10: float
    p50: float
    p90: float


class PriceForecast(_Model):
    model: str
    history: list[Bar]
    path: list[ForecastPoint]
    horizon: int
    sample_count: int
    last_close: float
    expected_move_pct: float
    range_low: float
    range_high: float


class Decision(_Model):
    rating: Rating
    confidence: Literal["low", "medium", "high"]
    summary: str
    rationale_md: str
    geo_statement: Literal["cites", "none_material", "unavailable"]
    cited_signal_ids: list[str]
    forecast_alignment: Literal["supports", "contradicts", "neutral", "unavailable"]
    missing_inputs: list[Literal["geo", "forecast"]]
    disclaimer: str = DISCLAIMER


class RunSummary(_Model):
    id: str
    ticker: str
    requested_date: dt.date
    analysis_date: dt.date
    status: RunStatus
    rating: Rating | None = None
    created_at: dt.datetime
    finished_at: dt.datetime | None = None
    retry_of: str | None = None


class RunPage(_Model):
    items: list[RunSummary]
    next_cursor: str | None = None


class RunDetail(RunSummary):
    stages: list[Stage]
    settings: dict[str, Any]
    llm_provider: str
    deep_model: str
    quick_model: str
    missing_inputs: list[str]
    error: str | None = None
    geo: GeoSummary | None = None
    forecast: PriceForecast | None = None
    decision: Decision | None = None
    last_event_seq: int = Field(
        description="Client passes this as Last-Event-ID when subscribing to events"
    )
