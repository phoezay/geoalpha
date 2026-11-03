"""T056: band quantiles and summary maths."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from geoalpha.forecast.kronos_service import (
    MIN_BARS,
    KronosForecaster,
    NotEnoughHistory,
    summarize,
    synthetic_forecast,
)


def _bars(n: int, last: float = 100.0) -> pd.DataFrame:
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(n)]
    close = np.linspace(last - n * 0.1, last, n)
    return pd.DataFrame(
        {
            "date": days,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.ones(n),
        }
    )


def test_quantiles_ordered_and_summary_consistent() -> None:
    rng = np.random.default_rng(0)
    samples = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, (30, 5)), axis=1))
    future = [date(2026, 7, 1) + timedelta(days=i) for i in range(5)]
    fc = summarize(model="m", bars=_bars(200), future_dates=future, sample_closes=samples)
    assert fc.horizon == len(fc.path) == 5
    assert all(p.p10 <= p.p50 <= p.p90 for p in fc.path)
    assert fc.expected_move_pct == pytest.approx(
        (fc.path[-1].p50 / fc.last_close - 1) * 100, abs=1e-3
    )
    assert (fc.range_low, fc.range_high) == (fc.path[-1].p10, fc.path[-1].p90)
    assert fc.sample_count == 30
    assert len(fc.history) == 120


def test_too_little_history_is_unavailable() -> None:
    with pytest.raises(NotEnoughHistory):
        synthetic_forecast(_bars(MIN_BARS - 1), date(2026, 7, 1))
    with pytest.raises(NotEnoughHistory):
        KronosForecaster("unused").forecast(_bars(10), date(2026, 7, 1))  # fails before loading


def test_synthetic_forecast_is_deterministic() -> None:
    a = synthetic_forecast(_bars(300), date(2026, 10, 30))
    b = synthetic_forecast(_bars(300), date(2026, 10, 30))
    assert a == b
