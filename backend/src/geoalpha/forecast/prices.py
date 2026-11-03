"""Daily OHLCV sources. Every source returns only bars dated on or before the analysis date
(Constitution I); the filter lives in one place, `_point_in_time`."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd

log = logging.getLogger(__name__)

COLUMNS = ["date", "open", "high", "low", "close", "volume"]
_FIXTURES = Path(__file__).parent / "fixtures"


class PriceSource(Protocol):
    def history(self, ticker: str, analysis_date: date, lookback: int) -> pd.DataFrame: ...


def _point_in_time(df: pd.DataFrame, analysis_date: date, lookback: int) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[df["date"] <= analysis_date].sort_values("date")
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df[COLUMNS].tail(lookback).reset_index(drop=True)


class FixturePriceSource:
    """Seeded synthetic bars for demo mode and tests (not real market data)."""

    def __init__(self, directory: Path = _FIXTURES) -> None:
        self.directory = directory

    def history(self, ticker: str, analysis_date: date, lookback: int) -> pd.DataFrame:
        path = self.directory / f"{ticker}.csv"
        if not path.exists():
            return pd.DataFrame(columns=COLUMNS)
        return _point_in_time(pd.read_csv(path), analysis_date, lookback)


class YFinancePriceSource:
    def history(self, ticker: str, analysis_date: date, lookback: int) -> pd.DataFrame:
        import yfinance as yf

        start = analysis_date - timedelta(days=int(lookback * 1.6) + 30)
        raw = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=(analysis_date + timedelta(days=1)).isoformat(),  # `end` is exclusive
            interval="1d",
            auto_adjust=False,
        )
        if raw is None or raw.empty:
            return pd.DataFrame(columns=COLUMNS)
        df = raw.reset_index().rename(columns=str.lower)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        return _point_in_time(df, analysis_date, lookback)
