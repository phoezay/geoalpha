from __future__ import annotations

from fastapi import APIRouter, Query, Request
from starlette.concurrency import run_in_threadpool

from geoalpha.api.schemas import TickerValidation
from geoalpha.core import tickers
from geoalpha.runner.fake_engine import FIXTURE_TICKERS

router = APIRouter()


def fixture_tickers_for(request: Request) -> frozenset[str]:
    return FIXTURE_TICKERS if request.app.state.settings.engine == "fake" else frozenset()


@router.get("/api/tickers/validate", operation_id="validateTicker", response_model=TickerValidation)
async def validate_ticker(request: Request, ticker: str = Query(...)) -> TickerValidation:
    """Inline ticker validation for the start form (FR-002)."""
    return await run_in_threadpool(
        tickers.validate, ticker, fixture_tickers=fixture_tickers_for(request)
    )
