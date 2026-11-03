"""Wires the optional pre-stages and their evidence sections into the pipeline."""

from __future__ import annotations

from geoalpha.agents import evidence
from geoalpha.core.settings import Settings
from geoalpha.runner import orchestrator


def register_features(settings: Settings) -> None:
    from geoalpha.forecast.stage import evidence_section as forecast_evidence
    from geoalpha.forecast.stage import make_forecast_stage
    from geoalpha.geo.stage import evidence_section as geo_evidence
    from geoalpha.geo.stage import make_geo_stage

    orchestrator.PRE_STAGES["forecast"] = make_forecast_stage(settings)
    orchestrator.PRE_STAGES["geo"] = make_geo_stage(settings)
    _add_section(geo_evidence)
    _add_section(forecast_evidence)


def _add_section(fn: evidence.SectionFn) -> None:
    if fn not in evidence.SECTIONS:
        evidence.SECTIONS.append(fn)
