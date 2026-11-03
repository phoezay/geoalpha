"""`geoalpha` command line."""

from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run the API and background worker."""
    import uvicorn

    uvicorn.run("geoalpha.api.app:create_app", factory=True, host=host, port=port, reload=reload)


@app.command()
def snapshot(
    watchlist: str = typer.Option(..., help="Comma-separated tickers, e.g. XOM,CVX,LMT"),
) -> None:
    """Record today's geopolitical snapshots for a watchlist (builds point-in-time history).

    Schedule daily (e.g. Windows Task Scheduler at 17:00 ET). No LLM assessment is run.
    """
    from collections import Counter

    from geoalpha.core import market_calendar
    from geoalpha.core.settings import get_settings
    from geoalpha.db.session import init_db
    from geoalpha.geo import analyst
    from geoalpha.geo.exposure import get_exposure
    from geoalpha.geo.provider import GeoSourceError, SnapshottingProvider
    from geoalpha.geo.stage import source_for

    settings = get_settings()
    init_db(settings.resolved_data_dir / "geoalpha.db")
    source = source_for(settings)
    if source is None:
        raise typer.BadParameter("GEOALPHA_GEO_PROVIDER=snapshot cannot record new snapshots")
    today = market_calendar.last_completed_session()
    fixture = settings.geo_provider == "fixture"
    for raw in watchlist.split(","):
        ticker = raw.strip().upper()
        if not ticker:
            continue
        provider = SnapshottingProvider(source, today)
        exposure = get_exposure(ticker, today, fixture=fixture)
        try:
            fetched = analyst.collect(provider, exposure)
        except GeoSourceError as exc:
            typer.echo(f"{ticker}: failed ({exc})", err=True)
            continue
        counts = Counter(f.tool for f in fetched)
        typer.echo(f"{ticker}: " + ", ".join(f"{t}x{n}" for t, n in sorted(counts.items())))


@app.command()
def version() -> None:
    """Print versions of GeoAlpha and its pinned upstreams."""
    import tradingagents

    typer.echo(f"geoalpha 0.1.0 · tradingagents {tradingagents.__version__}")


if __name__ == "__main__":
    app()
