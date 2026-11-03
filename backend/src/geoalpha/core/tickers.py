"""Ticker validation: US-listed equities and ETFs only (spec Assumptions)."""

from __future__ import annotations

import logging
import re
import time

from geoalpha.api.schemas import TickerValidation

log = logging.getLogger(__name__)

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_US_EXCHANGES = {"NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS", "NAS", "NYS", "NIM", "CBO"}
_TTL_S = 24 * 3600
_cache: dict[str, tuple[float, TickerValidation]] = {}


def normalize(ticker: str) -> str:
    return ticker.strip().upper()


def validate(ticker: str, *, fixture_tickers: frozenset[str] = frozenset()) -> TickerValidation:
    t = normalize(ticker)
    if not TICKER_RE.match(t):
        return TickerValidation(
            ticker=t, valid=False, reason="Use 1-10 letters, digits, '.' or '-'."
        )
    if t in fixture_tickers:
        return TickerValidation(ticker=t, valid=True, name=f"{t} (demo data)", exchange="DEMO")
    hit = _cache.get(t)
    if hit and time.monotonic() - hit[0] < _TTL_S:
        return hit[1]
    result = _lookup(t)
    if result.valid or result.reason != _UNREACHABLE:
        _cache[t] = (time.monotonic(), result)
    return result


_UNREACHABLE = "Could not reach market data to verify this ticker. Try again shortly."


def _lookup(t: str) -> TickerValidation:
    try:
        import yfinance as yf

        info = yf.Ticker(t).get_info()
    except Exception:  # noqa: BLE001 - network or upstream format errors
        log.warning("ticker lookup failed for %s", t, exc_info=True)
        return TickerValidation(ticker=t, valid=False, reason=_UNREACHABLE)
    quote_type = str(info.get("quoteType") or "").upper()
    exchange = str(info.get("exchange") or "")
    name = info.get("longName") or info.get("shortName")
    if not quote_type or not name:
        return TickerValidation(ticker=t, valid=False, reason="Ticker not found.")
    if quote_type not in ("EQUITY", "ETF"):
        return TickerValidation(
            ticker=t, valid=False, reason=f"Only stocks and ETFs are supported ({quote_type})."
        )
    if exchange not in _US_EXCHANGES:
        return TickerValidation(
            ticker=t,
            valid=False,
            exchange=exchange,
            reason="Only US-listed tickers are supported in this version.",
        )
    return TickerValidation(ticker=t, valid=True, name=str(name), exchange=exchange)
