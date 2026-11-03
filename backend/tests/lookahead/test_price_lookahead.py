"""T055: no price bar dated after the analysis date can reach the model (SC-005)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from geoalpha.forecast.kronos_service import synthetic_forecast
from geoalpha.forecast.prices import FixturePriceSource, _point_in_time


def _bars(start: str, end: str) -> pd.DataFrame:
    days = pd.bdate_range(start, end)
    n = len(days)
    return pd.DataFrame(
        {
            "date": days.date,
            "open": range(n),
            "high": range(n),
            "low": range(n),
            "close": [100 + i for i in range(n)],
            "volume": [1.0] * n,
        }
    )


def test_filter_drops_future_rows() -> None:
    analysis = date(2026, 6, 15)
    df = _point_in_time(_bars("2024-01-01", "2026-12-31"), analysis, 400)
    assert df["date"].max() == analysis
    assert (df["date"] <= analysis).all()
    assert len(df) == 400


def test_fixture_source_never_returns_future_bars(tmp_path: Path) -> None:
    _bars("2025-01-01", "2027-06-30").to_csv(tmp_path / "ABC.csv", index=False)
    analysis = date(2026, 3, 2)
    df = FixturePriceSource(tmp_path).history("ABC", analysis, 400)
    assert df["date"].max() <= analysis
    assert df.iloc[-1]["date"] == analysis


def test_forecast_starts_after_analysis_date_and_history_ends_on_it() -> None:
    analysis = date(2026, 6, 15)
    bars = _point_in_time(_bars("2025-01-01", "2026-12-31"), analysis, 400)
    fc = synthetic_forecast(bars, analysis)
    assert fc.history[-1].date == analysis
    assert all(p.date > analysis for p in fc.path)
    assert fc.last_close == float(bars["close"].iloc[-1])
