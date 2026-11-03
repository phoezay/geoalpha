from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from ulid import ULID

from geoalpha.api.app import ApiProblem
from geoalpha.api.routes_tickers import fixture_tickers_for
from geoalpha.api.schemas import RetryRequest, RunCreate, RunDetail, RunPage
from geoalpha.core import market_calendar, tickers
from geoalpha.core.settings import Settings
from geoalpha.db import repo
from geoalpha.db.models import AnalysisRun
from geoalpha.runner.worker import RunWorker

router = APIRouter()


def _settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


def _worker(request: Request) -> RunWorker:
    return request.app.state.worker  # type: ignore[no-any-return]


def _new_run(settings: Settings, ticker: str, requested: date, retry_of: str | None = None) -> str:
    run = AnalysisRun(
        id=str(ULID()),
        ticker=ticker,
        requested_date=requested,
        analysis_date=market_calendar.roll_back_to_session(requested),
        status="queued",
        llm_provider="offline demo" if settings.engine == "fake" else settings.llm_provider,
        deep_model="scripted" if settings.engine == "fake" else settings.deep_model,
        quick_model="scripted" if settings.engine == "fake" else settings.quick_model,
        settings={
            "engine": settings.engine,
            "geo_provider": settings.geo_provider,
            "max_debate_rounds": settings.max_debate_rounds,
            "forecast_horizon": 5,
            "forecast_samples": 30,
            "forecast_model": settings.forecast_model,
        },
        retry_of=retry_of,
        missing_inputs=[],
    )
    repo.create_run_with_stages(run)
    return run.id


@router.post(
    "/api/runs",
    operation_id="createRun",
    status_code=201,
    response_model=RunDetail,
    responses={422: {"model": None}, 503: {"model": None}},
)
async def create_run(request: Request, body: RunCreate) -> RunDetail:
    """Start an analysis run (FR-001). Returns immediately with all stages pending."""
    settings = _settings(request)
    if problems := settings.problems():
        raise ApiProblem(503, "GeoAlpha is not configured", " ".join(problems))

    requested = body.date or market_calendar.last_completed_session()
    if market_calendar.is_future(requested):
        raise ApiProblem(
            422,
            "Invalid input",
            "Check the highlighted fields.",
            {"date": "The analysis date cannot be in the future."},
        )
    check = await run_in_threadpool(
        tickers.validate, body.ticker, fixture_tickers=fixture_tickers_for(request)
    )
    if not check.valid:
        raise ApiProblem(
            422,
            "Invalid input",
            "Check the highlighted fields.",
            {"ticker": check.reason or "Unsupported ticker."},
        )

    run_id = await run_in_threadpool(_new_run, settings, check.ticker, requested)
    _worker(request).submit(run_id)
    return await run_in_threadpool(repo.get_run_detail, run_id)


@router.get("/api/runs", operation_id="listRuns", response_model=RunPage)
async def list_runs(
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None, description="ULID of the last item from the previous page"),
) -> RunPage:
    """Run history, newest first (FR-018)."""
    return await run_in_threadpool(repo.list_runs, limit, cursor)


@router.get(
    "/api/runs/{runId}",
    operation_id="getRun",
    response_model=RunDetail,
    responses={404: {"model": None}},
)
async def get_run(runId: str) -> RunDetail:  # noqa: N803
    """Full run snapshot (stages, signals, forecast, decision). Used on reload and from history."""
    return await run_in_threadpool(repo.get_run_detail, runId)


@router.post(
    "/api/runs/{runId}/retry",
    operation_id="retryRun",
    status_code=202,
    response_model=RunDetail,
    responses={409: {"model": None}},
)
async def retry_run(
    request: Request,
    runId: str,  # noqa: N803
    body: RetryRequest = Body(default_factory=RetryRequest),
) -> RunDetail:
    """Resume a failed/interrupted run from its checkpoint, or start a fresh linked run."""
    run = await run_in_threadpool(repo.get_run, runId)
    if body.mode == "fresh":
        if run.status not in ("completed", "failed", "interrupted"):
            raise ApiProblem(409, "Run still in progress", "Wait for it to finish first.")
        new_id = await run_in_threadpool(
            _new_run, _settings(request), run.ticker, run.requested_date, run.id
        )
        _worker(request).submit(new_id)
        return await run_in_threadpool(repo.get_run_detail, new_id)
    if run.status not in ("failed", "interrupted"):
        raise ApiProblem(
            409,
            "Nothing to resume",
            "Only failed or interrupted runs can be resumed. Use mode=fresh to re-run.",
        )
    await run_in_threadpool(repo.reset_stages_for_resume, runId)
    _worker(request).submit(runId, resume=True)
    return await run_in_threadpool(repo.get_run_detail, runId)


@router.get(
    "/api/runs/{runId}/export",
    operation_id="exportRun",
    response_class=Response,
    responses={
        200: {
            "content": {
                "text/markdown": {"schema": {"type": "string"}},
                "text/html": {"schema": {"type": "string"}},
            }
        },
        404: {"model": None},
        409: {"model": None},
    },
)
async def export_run(
    runId: str,  # noqa: N803
    format: str = Query(..., pattern="^(md|html)$"),  # noqa: A002 - name fixed by the contract
) -> Response:
    """Download a completed run as Markdown or self-contained HTML (FR-025)."""
    from geoalpha.api import export

    run = await run_in_threadpool(repo.get_run_detail, runId)
    if run.status != "completed":
        raise ApiProblem(409, "Run not finished", "Export is available once the run completes.")
    if format == "md":
        body, media = export.render_markdown(run), "text/markdown; charset=utf-8"
    else:
        body, media = export.render_html(run), "text/html; charset=utf-8"
    return Response(
        body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{export.filename(run, format)}"'},
    )
