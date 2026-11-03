"""NYSE session-date rules (America/New_York)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

ET = ZoneInfo("America/New_York")
_CLOSE_HOUR_ET = 16


@lru_cache(maxsize=1)
def _xnys() -> xcals.ExchangeCalendar:
    return xcals.get_calendar("XNYS", start="2000-01-01")


def now_et() -> datetime:
    return datetime.now(ET)


def today_et() -> date:
    return now_et().date()


def is_future(d: date) -> bool:
    return d > today_et()


def is_session(d: date) -> bool:
    return bool(_xnys().is_session(pd.Timestamp(d)))


def roll_back_to_session(d: date) -> date:
    """`d` itself if it is a session, else the previous session (weekends, holidays)."""
    cal = _xnys()
    ts = pd.Timestamp(d)
    if cal.is_session(ts):
        return d
    return cal.date_to_session(ts, direction="previous").date()  # type: ignore[no-any-return]


def last_completed_session(now: datetime | None = None) -> date:
    """Most recent session whose close has passed."""
    now = (now or now_et()).astimezone(ET)
    d = now.date()
    if is_session(d) and now.hour >= _CLOSE_HOUR_ET:
        return d
    return roll_back_to_session(d - timedelta(days=1))


def next_sessions(d: date, n: int) -> list[date]:
    """The `n` sessions strictly after `d`."""
    cal = _xnys()
    start = pd.Timestamp(d) + pd.Timedelta(days=1)
    sessions = cal.sessions_in_range(start, start + pd.Timedelta(days=n * 3 + 10))
    return [s.date() for s in sessions[:n]]
