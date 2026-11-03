"""Renders the "GeoAlpha Evidence" block appended to TradingAgents' `instrument_context`,
which every agent's prompt includes (research R1)."""

from __future__ import annotations

from collections.abc import Callable

from geoalpha.db import repo

HEADER = "### GeoAlpha Evidence"
FOOTER = "### End of GeoAlpha Evidence"

# Section renderers registered by the forecast (US3) and geo (US2) features.
# Each takes a run id and returns markdown lines, or [] when it has nothing to add.
SectionFn = Callable[[str], list[str]]
SECTIONS: list[SectionFn] = []


def render(run_id: str) -> str:
    repo.get_run(run_id)  # fail fast on an unknown run
    lines: list[str] = []
    for section in SECTIONS:
        lines.extend(section(run_id))
    if not lines:
        return ""
    return "\n".join(
        [
            "",
            HEADER,
            "Independent inputs gathered by GeoAlpha as of the analysis date. Weigh them with",
            "the other evidence and cite signal ids like [run:1] when they affect your view.",
            *lines,
            FOOTER,
        ]
    )
