"""Persistence operations. Each function owns its own short transaction so the worker
threads and the API never share a Session."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from geoalpha.api import schemas
from geoalpha.core.stages import STAGE_BY_KEY, STAGE_DEFS
from geoalpha.db.models import AnalysisRun, Decision, PriceForecastRow, RunEvent, Stage
from geoalpha.db.session import session_scope


def utcnow() -> datetime:
    """Naive UTC (SQLite stores no tz); `_utc` re-attaches it on the way out."""
    return datetime.now(UTC).replace(tzinfo=None)


def _utc(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


class NotFound(Exception):
    pass


def create_run_with_stages(run: AnalysisRun) -> schemas.RunDetail:
    """Insert the run and all 10 stage rows up front (SC-001: the full skeleton is known)."""
    with session_scope() as s:
        run.created_at = run.created_at or utcnow()
        run.stages = [
            Stage(key=d.key, order=i, critical=d.critical, timeout_s=d.timeout_s, status="pending")
            for i, d in enumerate(STAGE_DEFS)
        ]
        s.add(run)
    return get_run_detail(run.id)


def get_run(run_id: str) -> AnalysisRun:
    with session_scope() as s:
        run = s.get(AnalysisRun, run_id)
        if run is None:
            raise NotFound(run_id)
        s.expunge(run)
        return run


def _stage_schema(st: Stage) -> schemas.Stage:
    return schemas.Stage(
        key=st.key,
        label=STAGE_BY_KEY[st.key].label,
        order=st.order,
        critical=st.critical,
        status=st.status,
        started_at=_utc(st.started_at),
        finished_at=_utc(st.finished_at),
        attempts=st.attempts,
        report_md=st.report_md,
        payload=st.payload,
        error=st.error,
    )


def _decision_schema(d: Decision | None) -> schemas.Decision | None:
    if d is None:
        return None
    return schemas.Decision(
        rating=d.rating,
        confidence=d.confidence,
        summary=d.summary,
        rationale_md=d.rationale_md,
        geo_statement=d.geo_statement,
        cited_signal_ids=list(d.cited_signal_ids),
        forecast_alignment=d.forecast_alignment,
        missing_inputs=list(d.missing_inputs),
    )


def _summary_fields(run: AnalysisRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "ticker": run.ticker,
        "requested_date": run.requested_date,
        "analysis_date": run.analysis_date,
        "status": run.status,
        "rating": run.decision.rating if run.decision else None,
        "created_at": _utc(run.created_at),
        "finished_at": _utc(run.finished_at),
        "retry_of": run.retry_of,
    }


def _geo_summary(run_id: str) -> schemas.GeoSummary | None:
    from geoalpha.geo.stage import summary_for  # local: geo depends on repo

    return summary_for(run_id)


def _forecast_schema(row: PriceForecastRow | None) -> schemas.PriceForecast | None:
    return schemas.PriceForecast.model_validate(row.data) if row is not None else None


def save_forecast(run_id: str, forecast: schemas.PriceForecast) -> None:
    for p in forecast.path:
        if not p.p10 <= p.p50 <= p.p90:
            raise ValueError("forecast quantiles must satisfy p10 <= p50 <= p90")
    if len(forecast.path) != forecast.horizon:
        raise ValueError("forecast path length must equal the horizon")
    with session_scope() as s:
        row = s.get(PriceForecastRow, run_id)
        data = forecast.model_dump(mode="json")
        if row is None:
            s.add(PriceForecastRow(run_id=run_id, data=data))
        else:
            row.data = data


def get_forecast(run_id: str) -> schemas.PriceForecast | None:
    with session_scope() as s:
        return _forecast_schema(s.get(PriceForecastRow, run_id))


def get_run_detail(run_id: str) -> schemas.RunDetail:
    with session_scope() as s:
        run = s.get(AnalysisRun, run_id)
        if run is None:
            raise NotFound(run_id)
        last_seq = s.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id)) or 0
        detail = schemas.RunDetail(
            **_summary_fields(run),
            stages=[_stage_schema(st) for st in run.stages],
            settings=dict(run.settings or {}),
            llm_provider=run.llm_provider,
            deep_model=run.deep_model,
            quick_model=run.quick_model,
            missing_inputs=list(run.missing_inputs or []),
            error=run.error,
            decision=_decision_schema(run.decision),
            forecast=_forecast_schema(s.get(PriceForecastRow, run_id)),
            last_event_seq=last_seq,
        )
    # Outside the session: it opens its own, and nested sessions on one thread would wait on
    # the outer one's write lock (BEGIN IMMEDIATE, see db/session.py).
    detail.geo = _geo_summary(run_id)
    return detail


def list_runs(limit: int = 25, cursor: str | None = None) -> schemas.RunPage:
    """Newest first. ULIDs sort by creation time, so the id doubles as the cursor."""
    with session_scope() as s:
        q = select(AnalysisRun).order_by(AnalysisRun.id.desc()).limit(limit + 1)
        if cursor:
            q = q.where(AnalysisRun.id < cursor)
        rows = list(s.scalars(q))
        items = [schemas.RunSummary(**_summary_fields(r)) for r in rows[:limit]]
        next_cursor = rows[limit - 1].id if len(rows) > limit else None
        return schemas.RunPage(items=items, next_cursor=next_cursor)


def update_run(run_id: str, **fields: Any) -> None:
    with session_scope() as s:
        run = s.get(AnalysisRun, run_id)
        if run is None:
            raise NotFound(run_id)
        for k, v in fields.items():
            setattr(run, k, v)


def add_missing_input(run_id: str, key: str) -> None:
    with session_scope() as s:
        run = s.get(AnalysisRun, run_id)
        if run is not None and key not in (run.missing_inputs or []):
            run.missing_inputs = [*(run.missing_inputs or []), key]


def get_stage(run_id: str, key: str) -> Stage:
    with session_scope() as s:
        st = s.get(Stage, (run_id, key))
        if st is None:
            raise NotFound(f"{run_id}/{key}")
        s.expunge(st)
        return st


def update_stage(run_id: str, key: str, **fields: Any) -> None:
    with session_scope() as s:
        st = s.get(Stage, (run_id, key))
        if st is None:
            raise NotFound(f"{run_id}/{key}")
        for k, v in fields.items():
            setattr(st, k, v)


def reset_stages_for_resume(run_id: str) -> None:
    """Failed or unfinished critical stages go back to pending; finished ones are kept."""
    with session_scope() as s:
        run = s.get(AnalysisRun, run_id)
        if run is None:
            raise NotFound(run_id)
        for st in run.stages:
            if st.critical and st.status not in ("done", "skipped"):
                st.status, st.error, st.started_at, st.finished_at = "pending", None, None, None
        run.status, run.error, run.finished_at = "queued", None, None


def save_decision(run_id: str, decision: schemas.Decision) -> None:
    with session_scope() as s:
        existing = s.get(Decision, run_id)
        if existing is not None:
            s.delete(existing)
            s.flush()
        s.add(
            Decision(
                run_id=run_id,
                rating=decision.rating,
                confidence=decision.confidence,
                summary=decision.summary[:600],
                rationale_md=decision.rationale_md,
                geo_statement=decision.geo_statement,
                cited_signal_ids=list(decision.cited_signal_ids),
                forecast_alignment=decision.forecast_alignment,
                missing_inputs=list(decision.missing_inputs),
            )
        )


def append_event(run_id: str, type_: str, data: dict[str, Any]) -> tuple[int, datetime]:
    with session_scope() as s:
        last = s.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id)) or 0
        at = utcnow()
        s.add(RunEvent(run_id=run_id, seq=last + 1, type=type_, data=data, at=at))
        return last + 1, at.replace(tzinfo=UTC)


def events_after(run_id: str, seq: int) -> list[RunEvent]:
    with session_scope() as s:
        rows = list(
            s.scalars(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.seq > seq)
                .order_by(RunEvent.seq)
            )
        )
        for r in rows:
            s.expunge(r)
        return rows


def mark_running_as_interrupted() -> list[str]:
    """Startup recovery: runs that were mid-flight when the server stopped (FR-006)."""
    with session_scope() as s:
        rows = list(
            s.scalars(select(AnalysisRun).where(AnalysisRun.status.in_(("running", "queued"))))
        )
        for run in rows:
            run.status, run.finished_at = "interrupted", utcnow()
            run.error = "The server stopped while this run was in progress. Retry to resume."
            for st in run.stages:
                if st.status == "running":
                    st.status, st.error = "failed", "Interrupted by a server restart"
        return [r.id for r in rows]
