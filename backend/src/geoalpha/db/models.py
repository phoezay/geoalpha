"""SQLAlchemy models (data-model.md). All datetimes are UTC."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[str]: JSON}


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    requested_date: Mapped[date] = mapped_column(Date)
    analysis_date: Mapped[date] = mapped_column(Date)
    # queued | running | completed | failed | interrupted
    status: Mapped[str] = mapped_column(String(12), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    llm_provider: Mapped[str] = mapped_column(String(40))
    deep_model: Mapped[str] = mapped_column(String(80))
    quick_model: Mapped[str] = mapped_column(String(80))
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict)
    retry_of: Mapped[str | None] = mapped_column(ForeignKey("analysis_runs.id"))
    missing_inputs: Mapped[list[str]] = mapped_column(default=list)
    error: Mapped[str | None] = mapped_column(Text)

    stages: Mapped[list[Stage]] = relationship(
        back_populates="run", order_by="Stage.order", cascade="all, delete-orphan"
    )
    decision: Mapped[Decision | None] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Stage(Base):
    __tablename__ = "stages"

    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(20), primary_key=True)
    order: Mapped[int] = mapped_column(Integer)
    critical: Mapped[bool]
    # pending | running | done | failed | unavailable | skipped
    status: Mapped[str] = mapped_column(String(12), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    timeout_s: Mapped[int] = mapped_column(Integer)
    report_md: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    run: Mapped[AnalysisRun] = relationship(back_populates="stages")


class Decision(Base):
    __tablename__ = "decisions"

    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), primary_key=True)
    rating: Mapped[str] = mapped_column(String(12))  # Buy|Overweight|Hold|Underweight|Sell
    confidence: Mapped[str] = mapped_column(String(6))  # low|medium|high
    summary: Mapped[str] = mapped_column(String(600))
    rationale_md: Mapped[str] = mapped_column(Text)
    geo_statement: Mapped[str] = mapped_column(String(14))  # cites|none_material|unavailable
    cited_signal_ids: Mapped[list[str]] = mapped_column(default=list)
    # supports|contradicts|neutral|unavailable
    forecast_alignment: Mapped[str] = mapped_column(String(12))
    missing_inputs: Mapped[list[str]] = mapped_column(default=list)

    run: Mapped[AnalysisRun] = relationship(back_populates="decision")


class RunEvent(Base):
    __tablename__ = "run_events"

    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(24))
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
    at: Mapped[datetime] = mapped_column(DateTime)


class PriceForecastRow(Base):
    """Kronos forecast for a run. `path` holds {date, p10, p50, p90} with p10 <= p50 <= p90
    and len(path) == horizon; every `history` bar is dated on or before the analysis date."""

    __tablename__ = "price_forecasts"

    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)  # schemas.PriceForecast, as JSON


class GeoSnapshot(Base):
    """A raw WorldMonitor response as captured. Immutable: `captured_at` is the honest fetch
    time, which is what makes later point-in-time eligibility checks possible."""

    __tablename__ = "geo_snapshots"
    __table_args__ = (Index("ix_geo_snap_lookup", "tool", "params_hash", "captured_at"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    tool: Mapped[str] = mapped_column(String(60))
    params_hash: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    payload: Mapped[Any] = mapped_column(JSON)
    as_of: Mapped[date] = mapped_column(Date)
    captured_at: Mapped[datetime] = mapped_column(DateTime)
    source_mode: Mapped[str] = mapped_column(String(12))  # hosted|self_hosted|fixture


class ExposureProfileRow(Base):
    """Countries (1-6, weights 0-1 summing to <= 1), commodities, chokepoints, themes (<= 5)
    for a ticker, cached per quarter (YYYYQn)."""

    __tablename__ = "exposure_profiles"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    quarter: Mapped[str] = mapped_column(String(6), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class RunGeoSignal(Base):
    """A ranked, sourced signal assessed for one run. `snapshot_id` is required: no
    unsourced signals (Constitution II)."""

    __tablename__ = "run_geo_signals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # "{run_id}:{rank}"
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)  # 1-10
    region: Mapped[str] = mapped_column(String(60))
    # conflict|instability|sanctions|supply_route|commodity_shock|energy|cyber|disaster|policy|other
    category: Mapped[str] = mapped_column(String(20))
    severity: Mapped[int] = mapped_column(Integer)  # 1-5
    impact_direction: Mapped[str] = mapped_column(String(10))  # positive|negative|mixed|uncertain
    headline: Mapped[str] = mapped_column(String(140))
    rationale: Mapped[str] = mapped_column(Text)
    valid_at: Mapped[datetime] = mapped_column(DateTime)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("geo_snapshots.id"))
    source_label: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(500))
