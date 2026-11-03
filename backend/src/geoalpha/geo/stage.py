"""The `geo` pre-stage (US2) and its evidence section."""

from __future__ import annotations

import logging
from typing import Any

from geoalpha.api import schemas
from geoalpha.core.settings import Settings
from geoalpha.db import repo
from geoalpha.geo import analyst, store
from geoalpha.geo.exposure import get_exposure
from geoalpha.geo.fixture import FixtureGeoSource
from geoalpha.geo.provider import GeoSource, GeoSourceError, GeoUnavailable, SnapshottingProvider
from geoalpha.runner.orchestrator import PreStageFn, PreStageResult, RunContext, Unavailable

log = logging.getLogger(__name__)

_IMPACT_WORD = {
    "positive": "tailwind",
    "negative": "headwind",
    "mixed": "mixed",
    "uncertain": "unclear",
}


def source_for(settings: Settings) -> GeoSource | None:
    if settings.geo_provider == "fixture":
        return FixtureGeoSource()
    if settings.geo_provider == "worldmonitor":
        from geoalpha.geo.worldmonitor import WorldMonitorSource

        return WorldMonitorSource(settings)
    return None  # "snapshot": recorded data only, never live


def _quick_llm(settings: Settings) -> Any:
    from tradingagents.llm_clients import create_tier_client

    from geoalpha.agents.graph import build_config

    config = build_config(
        data_dir=settings.resolved_data_dir,
        llm_provider=settings.llm_provider,
        deep_model=settings.deep_model,
        quick_model=settings.quick_model,
    )
    return create_tier_client(config, "quick").get_llm()


def make_geo_stage(settings: Settings, source: GeoSource | None = None) -> PreStageFn:
    src = source if source is not None else source_for(settings)
    deterministic = settings.geo_provider == "fixture" or settings.engine == "fake"

    def run(ctx: RunContext) -> PreStageResult:
        provider = SnapshottingProvider(src, ctx.analysis_date)
        llm = None if deterministic else _quick_llm(settings)
        exposure = get_exposure(ctx.ticker, ctx.analysis_date, fixture=deterministic, quick_llm=llm)
        try:
            fetched = analyst.collect(provider, exposure)
        except GeoUnavailable as exc:
            raise Unavailable(str(exc)) from exc
        except GeoSourceError:
            raise
        drafts = (
            analyst.deterministic_assess(fetched, exposure, ctx.ticker, ctx.analysis_date)
            if llm is None
            else analyst.llm_assess(llm, fetched, exposure, ctx.ticker, ctx.analysis_date)
        )
        pairs = analyst.finalize(
            ctx.run_id, drafts, fixture=src is not None and src.mode == "fixture"
        )
        store.save_signals(ctx.run_id, pairs)
        signals = [s for s, _ in pairs]
        summary = schemas.GeoSummary(
            materiality=analyst.materiality(signals),
            exposure=schemas.Exposure.model_validate(exposure.model_dump()),
            signals=signals,
        )
        return PreStageResult(
            report_md=_narrative(ctx.ticker, summary),
            payload={
                "materiality": summary.materiality,
                "exposure": summary.exposure.model_dump() if summary.exposure else None,
                "signal_count": len(signals),
                "live_calls": provider.live_calls,
            },
            ready_event=("geo.ready", summary.model_dump(mode="json")),
        )

    return run


def _narrative(ticker: str, g: schemas.GeoSummary) -> str:
    if not g.signals or g.materiality == "immaterial":
        return f"No material geopolitical exposure detected for {ticker}."
    lines = [f"**{len(g.signals)} geopolitical signals** relevant to {ticker}:"]
    for s in g.signals[:5]:
        lines.append(
            f"- [{s.id.split(':')[-1]}] {s.region} · {s.category.replace('_', ' ')} · severity "
            f"{s.severity}/5 · {_IMPACT_WORD[s.impact_direction]}: {s.headline}"
        )
    return "\n".join(lines)


def summary_for(run_id: str) -> schemas.GeoSummary | None:
    st = repo.get_stage(run_id, "geo")
    if st.status == "unavailable":
        return schemas.GeoSummary(materiality="unavailable", unavailable_reason=st.error)
    if st.status != "done":
        return None
    payload = st.payload or {}
    exposure = payload.get("exposure")
    return schemas.GeoSummary(
        materiality=payload.get("materiality", "immaterial"),
        exposure=schemas.Exposure.model_validate(exposure) if exposure else None,
        signals=store.load_signals(run_id),
    )


def evidence_section(run_id: str) -> list[str]:
    st = repo.get_stage(run_id, "geo")
    if st.status in ("failed", "unavailable"):
        return [
            "- Geopolitics: data unavailable for this analysis date. Do not assume the "
            "absence of geopolitical risk."
        ]
    g = summary_for(run_id)
    if g is None:
        return []
    if g.materiality == "immaterial" or not g.signals:
        return ["- Geopolitics: no material exposure detected for this ticker."]
    out = ["- Geopolitical signals (cite by id):"]
    for s in g.signals[:6]:
        out.append(
            f"  - [{s.id}] {s.region} · {s.category} · sev {s.severity} · {s.impact_direction}: "
            f"{s.headline} (source: {s.source_label}, valid {s.valid_at.date().isoformat()})"
        )
    return out
