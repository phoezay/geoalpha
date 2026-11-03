"""The `forecast` pre-stage (US3): point-in-time bars -> Kronos sample band -> evidence."""

from __future__ import annotations

from geoalpha.core.settings import Settings
from geoalpha.db import repo
from geoalpha.forecast.kronos_service import (
    KronosForecaster,
    NotEnoughHistory,
    synthetic_forecast,
)
from geoalpha.forecast.prices import FixturePriceSource, PriceSource, YFinancePriceSource
from geoalpha.runner.orchestrator import PreStageFn, PreStageResult, RunContext, Unavailable

LOOKBACK = 400


def price_source_for(settings: Settings) -> PriceSource:
    return FixturePriceSource() if settings.engine == "fake" else YFinancePriceSource()


def make_forecast_stage(settings: Settings, source: PriceSource | None = None) -> PreStageFn:
    prices = source or price_source_for(settings)
    forecaster = None if settings.fake_forecast else KronosForecaster(settings.forecast_model)

    def run(ctx: RunContext) -> PreStageResult:
        horizon = int(ctx.settings.get("forecast_horizon", 5))
        samples = int(ctx.settings.get("forecast_samples", 30))
        bars = prices.history(ctx.ticker, ctx.analysis_date, LOOKBACK)
        try:
            if forecaster is None:
                fc = synthetic_forecast(bars, ctx.analysis_date, horizon, samples)
            else:
                fc = forecaster.forecast(bars, ctx.analysis_date, horizon, samples)
        except NotEnoughHistory as exc:
            raise Unavailable(str(exc)) from exc
        repo.save_forecast(ctx.run_id, fc)
        report = (
            f"Expected move **{fc.expected_move_pct:+.1f}%** over {fc.horizon} sessions "
            f"(p10–p90 at horizon: {fc.range_low:.2f}–{fc.range_high:.2f}; "
            f"last close {fc.last_close:.2f}; {fc.sample_count} sample paths, {fc.model})."
        )
        return PreStageResult(
            report_md=report,
            payload={"expected_move_pct": fc.expected_move_pct, "model": fc.model},
            ready_event=("forecast.ready", fc.model_dump(mode="json")),
        )

    return run


def evidence_section(run_id: str) -> list[str]:
    fc = repo.get_forecast(run_id)
    if fc is None:
        stage = repo.get_stage(run_id, "forecast")
        if stage.status in ("failed", "unavailable"):
            return ["- Price model: no forecast available for this run."]
        return []
    return [
        f"- Price model ({fc.model}, {fc.sample_count} samples): expected "
        f"{fc.expected_move_pct:+.1f}% over {fc.horizon} sessions; p10–p90 range at horizon "
        f"{fc.range_low:.2f}–{fc.range_high:.2f} vs last close {fc.last_close:.2f}. "
        "Treat as one probabilistic input, not a target."
    ]
