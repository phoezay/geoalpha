"""T067: geopolitical point-in-time rule (FR-009, SC-005, Constitution I)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from geoalpha.core import market_calendar
from geoalpha.db.session import init_db
from geoalpha.geo import provider as gp
from geoalpha.geo.provider import GeoUnavailable, SnapshottingProvider, store_snapshot


class SpySource:
    mode = "fixture"

    def __init__(self) -> None:
        self.calls = 0

    def call(self, tool: str, params: dict[str, Any]) -> Any:
        self.calls += 1
        return {"live": True}


@pytest.fixture(autouse=True)
def db(tmp_path: Path) -> None:
    init_db(tmp_path / "geo.db")


PAST = date(2026, 6, 15)  # a Monday, well before "now"
TOOL, PARAMS = "get_country_risk", {"country_code": "SA"}


def _et(d: date, hh: int, mm: int = 0, ss: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=market_calendar.ET)


def _store(payload: dict[str, Any], when: datetime) -> None:
    store_snapshot(TOOL, PARAMS, payload, captured_at=when, as_of=PAST)


def test_past_date_without_snapshot_is_unavailable_and_never_live() -> None:
    spy = SpySource()
    p = SnapshottingProvider(spy, PAST)
    with pytest.raises(GeoUnavailable):
        p.fetch(TOOL, PARAMS)
    assert spy.calls == 0 and p.live_calls == 0


def test_snapshot_captured_after_the_date_is_never_eligible() -> None:
    _store({"v": "next-morning"}, _et(PAST + timedelta(days=1), 8))
    with pytest.raises(GeoUnavailable):
        SnapshottingProvider(SpySource(), PAST).fetch(TOOL, PARAMS)


def test_snapshot_older_than_window_is_not_eligible() -> None:
    _store({"v": "stale"}, _et(PAST - timedelta(days=4), 12))
    with pytest.raises(GeoUnavailable):
        SnapshottingProvider(SpySource(), PAST).fetch(TOOL, PARAMS)


def test_latest_eligible_snapshot_wins() -> None:
    _store({"v": "two-days-before"}, _et(PAST - timedelta(days=2), 17))
    _store({"v": "same-evening"}, _et(PAST, 23, 30))
    _store({"v": "after"}, _et(PAST + timedelta(days=1), 0, 5))
    got = SnapshottingProvider(SpySource(), PAST).fetch(TOOL, PARAMS)
    assert got.payload == {"v": "same-evening"}


def test_current_session_goes_live_and_persists_snapshot() -> None:
    spy = SpySource()
    current = market_calendar.last_completed_session()
    got = SnapshottingProvider(spy, current).fetch(TOOL, PARAMS)
    assert spy.calls == 1 and got.payload == {"live": True}
    assert got.captured_at <= datetime.now(UTC)
    # Its honest capture time means it can never serve a backtest of an earlier date.
    with pytest.raises(GeoUnavailable):
        SnapshottingProvider(None, current - timedelta(days=7)).fetch(TOOL, PARAMS)


def test_snapshot_provider_never_calls_live() -> None:
    assert SnapshottingProvider(None, market_calendar.today_et()).live is False


def test_window_bounds() -> None:
    start, end = gp.eligibility_window(PAST)
    assert end.replace(tzinfo=UTC) == _et(PAST, 23, 59, 59).astimezone(UTC)
    assert end - start > timedelta(days=3)
