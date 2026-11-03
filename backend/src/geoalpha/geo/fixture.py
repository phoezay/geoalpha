"""Deterministic demo source shaped like WorldMonitor tool responses (not real events)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).parent / "fixtures"
SOURCE_LABEL = "WorldMonitor (demo fixture)"
SOURCE_URL = "https://www.worldmonitor.app"


@cache
def _load(name: str) -> Any:
    return json.loads((_DIR / name).read_text(encoding="utf-8"))


def exposure_fixture(ticker: str) -> dict[str, Any] | None:
    data: dict[str, Any] = _load("exposure.json")
    return data.get(ticker)


class FixtureGeoSource:
    mode = "fixture"

    def call(self, tool: str, params: dict[str, Any]) -> Any:
        countries: dict[str, Any] = _load("countries.json")
        cc = str(params.get("country_code") or params.get("country") or "").upper()
        entry = countries.get(cc, {})
        match tool:
            case "get_world_brief":
                return _load("world_brief.json")
            case "get_country_risk":
                return entry.get("risk", {"country_code": cc, "cii_score": None, "band": "unknown"})
            case "get_conflict_events":
                return {
                    "country": cc,
                    "events": entry.get("conflicts", [])[: params.get("limit", 10)],
                }
            case "get_sanctions_data":
                return {"country": cc, "designations": entry.get("sanctions", [])}
            case "get_maritime_activity":
                return entry.get("maritime", {"country_code": cc, "disruptions": []})
        raise ValueError(f"fixture source has no tool {tool}")
