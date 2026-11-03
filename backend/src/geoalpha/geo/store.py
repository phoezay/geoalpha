"""Persistence for per-run geopolitical results."""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import delete, select

from geoalpha.api import schemas
from geoalpha.db.models import RunGeoSignal
from geoalpha.db.session import session_scope


def save_signals(run_id: str, pairs: list[tuple[schemas.GeoSignal, str]]) -> None:
    with session_scope() as s:
        s.execute(delete(RunGeoSignal).where(RunGeoSignal.run_id == run_id))
        for sig, snapshot_id in pairs:
            if not snapshot_id or not sig.source_label:
                continue  # Constitution II: never persist an unsourced signal
            s.add(
                RunGeoSignal(
                    id=sig.id,
                    run_id=run_id,
                    rank=sig.rank,
                    region=sig.region,
                    category=sig.category,
                    severity=sig.severity,
                    impact_direction=sig.impact_direction,
                    headline=sig.headline,
                    rationale=sig.rationale,
                    valid_at=sig.valid_at.astimezone(UTC).replace(tzinfo=None),
                    snapshot_id=snapshot_id,
                    source_label=sig.source_label,
                    source_url=sig.source_url,
                )
            )


def load_signals(run_id: str) -> list[schemas.GeoSignal]:
    with session_scope() as s:
        rows = s.scalars(
            select(RunGeoSignal).where(RunGeoSignal.run_id == run_id).order_by(RunGeoSignal.rank)
        )
        return [
            schemas.GeoSignal(
                id=r.id,
                rank=r.rank,
                region=r.region,
                category=r.category,
                severity=r.severity,
                impact_direction=r.impact_direction,
                headline=r.headline,
                rationale=r.rationale,
                valid_at=r.valid_at.replace(tzinfo=UTC),
                source_label=r.source_label,
                source_url=r.source_url,
            )
            for r in rows
        ]
