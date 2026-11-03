"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from geoalpha.core import market_calendar
from geoalpha.core.logging import configure_logging
from geoalpha.core.settings import Settings, get_settings
from geoalpha.db import repo
from geoalpha.db.session import init_db
from geoalpha.runner.orchestrator import Engine
from geoalpha.runner.worker import RunWorker

PROBLEM = "application/problem+json"


class ApiProblem(Exception):
    def __init__(
        self,
        status: int,
        title: str,
        detail: str | None = None,
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(title)
        self.status, self.title, self.detail, self.field_errors = (
            status,
            title,
            detail,
            field_errors,
        )


def _problem(
    status: int, title: str, detail: str | None = None, field_errors: dict[str, str] | None = None
) -> JSONResponse:
    body: dict[str, object] = {"title": title, "status": status}
    if detail:
        body["detail"] = detail
    if field_errors:
        body["field_errors"] = field_errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM)


def create_app(
    settings: Settings | None = None, engine: Engine | None = None, db_path: str | None = None
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        # Building the NYSE calendar takes ~1 s; do it now, not on the first POST (SC-001).
        market_calendar.last_completed_session()
        init_db(db_path or settings.resolved_data_dir / "geoalpha.db")
        worker = RunWorker(settings, engine)
        worker.recover()
        app.state.worker = worker
        try:
            yield
        finally:
            worker.shutdown()

    app = FastAPI(
        title="GeoAlpha API",
        version="0.1.0",
        description="Local research API for GeoAlpha. Research output only, not financial advice.",
        lifespan=lifespan,
    )
    app.state.settings = settings

    @app.exception_handler(ApiProblem)
    async def _api_problem(_: Request, exc: ApiProblem) -> JSONResponse:
        return _problem(exc.status, exc.title, exc.detail, exc.field_errors)

    @app.exception_handler(repo.NotFound)
    async def _not_found(_: Request, exc: repo.NotFound) -> JSONResponse:
        return _problem(404, "Not found", f"No run with id {exc}")

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = {
            str(err["loc"][-1]): str(err["msg"]).removeprefix("Value error, ")
            for err in exc.errors()
            if err.get("loc")
        }
        return _problem(422, "Invalid input", "Check the highlighted fields.", fields)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException) -> JSONResponse:
        return _problem(exc.status_code, str(exc.detail))

    from geoalpha.api import routes_events, routes_health, routes_runs, routes_tickers

    app.include_router(routes_health.router)
    app.include_router(routes_tickers.router)
    app.include_router(routes_runs.router)
    app.include_router(routes_events.router)
    return app
