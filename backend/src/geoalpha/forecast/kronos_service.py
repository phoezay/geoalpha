"""Kronos price forecast with an uncertainty band (research R6).

Kronos averages its samples internally, so one call gives no spread. Instead, `predict_batch`
runs N copies of the same history with `sample_count=1`: N independent sample paths, from which
we take per-step p10/p50/p90 of the close.
"""

from __future__ import annotations

import logging
import threading
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from geoalpha.api import schemas
from geoalpha.core import market_calendar

log = logging.getLogger(__name__)

TOKENIZER_ID = "NeoQuasar/Kronos-Tokenizer-base"
MIN_BARS = 120
HISTORY_SHOWN = 120


class NotEnoughHistory(Exception):
    pass


def summarize(
    *,
    model: str,
    bars: pd.DataFrame,
    future_dates: list[date],
    sample_closes: np.ndarray,  # shape (samples, horizon)
) -> schemas.PriceForecast:
    """Quantiles + summary from sample paths. Pure function (unit-tested without torch)."""
    p10, p50, p90 = np.percentile(sample_closes, [10, 50, 90], axis=0)
    last_close = float(bars["close"].iloc[-1])
    path = [
        schemas.ForecastPoint(date=d, p10=float(a), p50=float(b), p90=float(c))
        for d, a, b, c in zip(future_dates, p10, p50, p90, strict=True)
    ]
    shown = bars.tail(HISTORY_SHOWN)
    history = [
        schemas.Bar(
            date=r.date,
            open=float(r.open),
            high=float(r.high),
            low=float(r.low),
            close=float(r.close),
            volume=float(r.volume) if pd.notna(r.volume) else None,
        )
        for r in shown.itertuples(index=False)
    ]
    return schemas.PriceForecast(
        model=model,
        history=history,
        path=path,
        horizon=len(path),
        sample_count=int(sample_closes.shape[0]),
        last_close=last_close,
        expected_move_pct=round((float(p50[-1]) / last_close - 1) * 100, 3),
        range_low=float(p10[-1]),
        range_high=float(p90[-1]),
    )


class KronosForecaster:
    """Loads the model once per process and keeps it warm."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self._predictor: Any = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        with self._lock:
            if self._predictor is None:
                import torch

                from geoalpha.vendor.kronos.model import Kronos, KronosPredictor, KronosTokenizer

                log.info("loading %s", self.model_id)
                tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_ID)
                model = Kronos.from_pretrained(self.model_id)
                tokenizer.eval()
                model.eval()
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
                self._predictor = KronosPredictor(model, tokenizer, device=device, max_context=512)
            return self._predictor

    def forecast(
        self, bars: pd.DataFrame, analysis_date: date, horizon: int = 5, samples: int = 30
    ) -> schemas.PriceForecast:
        if len(bars) < MIN_BARS:
            raise NotEnoughHistory(
                f"Not enough price history to forecast ({len(bars)} of {MIN_BARS} trading days)."
            )
        import torch

        predictor = self._load()
        future = market_calendar.next_sessions(analysis_date, horizon)
        x_ts = pd.Series(pd.to_datetime(bars["date"]))
        y_ts = pd.Series(pd.to_datetime(future))
        frame = bars[["open", "high", "low", "close", "volume"]].astype("float64")
        with torch.no_grad():
            preds = predictor.predict_batch(
                [frame] * samples,
                [x_ts] * samples,
                [y_ts] * samples,
                pred_len=horizon,
                T=1.0,
                top_p=0.9,
                sample_count=1,
                verbose=False,
            )
        closes = np.stack([np.asarray(p["close"], dtype=float) for p in preds])
        return summarize(
            model=self.model_id,
            bars=bars,
            future_dates=future,
            sample_closes=closes,
        )


def synthetic_forecast(
    bars: pd.DataFrame, analysis_date: date, horizon: int = 5, samples: int = 30, seed: int = 7
) -> schemas.PriceForecast:
    """Deterministic stand-in (GEOALPHA_FAKE_FORECAST=1): a seeded random walk sized by the
    bars' own volatility. Used for fast e2e runs; labelled as synthetic in the model name."""
    if len(bars) < MIN_BARS:
        raise NotEnoughHistory(
            f"Not enough price history to forecast ({len(bars)} of {MIN_BARS} trading days)."
        )
    closes = bars["close"].astype(float).to_numpy()
    rets = np.diff(np.log(closes))
    rng = np.random.default_rng(seed + len(bars))
    steps = rng.normal(rets[-60:].mean(), rets[-60:].std(), size=(samples, horizon))
    paths = closes[-1] * np.exp(np.cumsum(steps, axis=1))
    return summarize(
        model="synthetic (demo)",
        bars=bars,
        future_dates=market_calendar.next_sessions(analysis_date, horizon),
        sample_closes=paths,
    )
