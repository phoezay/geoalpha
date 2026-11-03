"""Geopolitical data access with the point-in-time rule (research R4, Constitution I).

A `GeoSource` answers live calls (WorldMonitor, or deterministic fixtures). Callers never use a
source directly: `SnapshottingProvider` decides per analysis date whether a live call is allowed
(current session only) and persists every live answer as an immutable `GeoSnapshot`. For any
earlier date, only snapshots captured on or before that date's end (ET) and no more than three
days earlier are eligible; otherwise the data is `unavailable`. It is never silently replaced by
today's data.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol

from sqlalchemy import select
from ulid import ULID

from geoalpha.core import market_calendar
from geoalpha.db.models import GeoSnapshot
from geoalpha.db.session import session_scope

LOOKBACK_DAYS = 3


class GeoUnavailable(Exception):
    """No eligible data for this date (distinct from a source failure)."""


class GeoSourceError(Exception):
    """The live source failed (auth, network, upstream error). Message is user-facing."""


class GeoSource(Protocol):
    mode: str  # hosted | self_hosted | fixture

    def call(self, tool: str, params: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class Fetched:
    snapshot_id: str
    payload: Any
    captured_at: datetime  # UTC
    tool: str
    params: dict[str, Any]


def params_hash(tool: str, params: dict[str, Any]) -> str:
    canonical = json.dumps({"tool": tool, **params}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def is_current_session(d: date) -> bool:
    return d >= market_calendar.last_completed_session() or d == market_calendar.today_et()


def eligibility_window(d: date) -> tuple[datetime, datetime]:
    """[start, end] in naive UTC for snapshots usable for analysis date `d`."""
    end_et = datetime.combine(d, time(23, 59, 59), tzinfo=market_calendar.ET)
    start_et = datetime.combine(
        d - timedelta(days=LOOKBACK_DAYS), time(0, 0), tzinfo=market_calendar.ET
    )
    return (
        start_et.astimezone(UTC).replace(tzinfo=None),
        end_et.astimezone(UTC).replace(tzinfo=None),
    )


class SnapshottingProvider:
    def __init__(self, source: GeoSource | None, analysis_date: date) -> None:
        self.source = source
        self.analysis_date = analysis_date
        self.live = source is not None and is_current_session(analysis_date)
        self.live_calls = 0

    def fetch(self, tool: str, params: dict[str, Any]) -> Fetched:
        if self.live:
            return self._fetch_live(tool, params)
        return self._latest_eligible(tool, params)

    def _fetch_live(self, tool: str, params: dict[str, Any]) -> Fetched:
        assert self.source is not None
        self.live_calls += 1
        payload = self.source.call(tool, params)
        captured = datetime.now(UTC).replace(tzinfo=None)
        snap = GeoSnapshot(
            id=str(ULID()),
            tool=tool,
            params_hash=params_hash(tool, params),
            params=params,
            payload=payload,
            as_of=self.analysis_date,
            captured_at=captured,
            source_mode=self.source.mode,
        )
        with session_scope() as s:
            s.add(snap)
        return Fetched(snap.id, payload, captured.replace(tzinfo=UTC), tool, params)

    def _latest_eligible(self, tool: str, params: dict[str, Any]) -> Fetched:
        start, end = eligibility_window(self.analysis_date)
        with session_scope() as s:
            snap = s.scalars(
                select(GeoSnapshot)
                .where(
                    GeoSnapshot.tool == tool,
                    GeoSnapshot.params_hash == params_hash(tool, params),
                    GeoSnapshot.captured_at >= start,
                    GeoSnapshot.captured_at <= end,
                )
                .order_by(GeoSnapshot.captured_at.desc())
                .limit(1)
            ).first()
            if snap is None:
                raise GeoUnavailable(
                    f"Geopolitical data unavailable for {self.analysis_date.isoformat()}: no "
                    "snapshot was recorded on or shortly before that date."
                )
            return Fetched(
                snap.id, snap.payload, snap.captured_at.replace(tzinfo=UTC), tool, params
            )


def store_snapshot(
    tool: str,
    params: dict[str, Any],
    payload: Any,
    *,
    captured_at: datetime,
    as_of: date,
    mode: str = "fixture",
) -> str:
    """Insert a snapshot with an explicit capture time (tests and backfills)."""
    snap = GeoSnapshot(
        id=str(ULID()),
        tool=tool,
        params_hash=params_hash(tool, params),
        params=params,
        payload=payload,
        as_of=as_of,
        captured_at=captured_at.astimezone(UTC).replace(tzinfo=None),
        source_mode=mode,
    )
    with session_scope() as s:
        s.add(snap)
    return snap.id
