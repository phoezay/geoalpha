"""T058: real Kronos-small on CPU (downloads weights; run with `pytest -m integration`)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from geoalpha.forecast.kronos_service import KronosForecaster


@pytest.mark.integration
def test_kronos_small_forecast_shape() -> None:
    rng = np.random.default_rng(1)
    days = pd.bdate_range(end="2026-10-30", periods=200)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 200)))
    bars = pd.DataFrame(
        {
            "date": days.date,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": rng.lognormal(12, 0.3, 200),
        }
    )
    fc = KronosForecaster("NeoQuasar/Kronos-small").forecast(bars, date(2026, 10, 30), 5, 4)
    assert len(fc.path) == 5 and fc.sample_count == 4
    assert all(np.isfinite([p.p10, p.p50, p.p90]).all() for p in fc.path)
    assert all(p.p10 <= p.p50 <= p.p90 for p in fc.path)
