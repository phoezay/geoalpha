"""WorldMonitor via its MIT-licensed Python SDK (the AGPL platform is only called, never
vendored). Works against the hosted API (Pro key) or a self-hosted stack (base/MCP URL)."""

from __future__ import annotations

import logging
from typing import Any

from geoalpha.core.settings import Settings
from geoalpha.geo.provider import GeoSourceError

log = logging.getLogger(__name__)

# Server-side projections keep payloads small (80-95% cut per WorldMonitor docs).
_PROJECTIONS: dict[str, str] = {}


class WorldMonitorSource:
    def __init__(self, settings: Settings) -> None:
        from worldmonitor_sdk import Client

        kwargs: dict[str, Any] = {"timeout": 30.0}
        if settings.worldmonitor_api_key:
            kwargs["api_key"] = settings.worldmonitor_api_key
        if settings.worldmonitor_base_url:
            kwargs["base_url"] = settings.worldmonitor_base_url
        if settings.worldmonitor_mcp_url:
            kwargs["mcp_url"] = settings.worldmonitor_mcp_url
        self.client = Client(**kwargs)
        self.mode = "self_hosted" if settings.worldmonitor_base_url else "hosted"

    def call(self, tool: str, params: dict[str, Any]) -> Any:
        from worldmonitor_sdk import APIError, MCPError

        args = dict(params)
        if tool in _PROJECTIONS:
            args["jmespath"] = _PROJECTIONS[tool]
        try:
            return self.client.call_tool(tool, args)
        except MCPError as exc:
            log.warning("WorldMonitor MCP error on %s: %s", tool, exc)
            text = str(exc).lower()
            if "key" in text or "auth" in text or "unauthor" in text:
                raise GeoSourceError("WorldMonitor rejected the API key.") from exc
            raise GeoSourceError(f"WorldMonitor could not answer {tool}.") from exc
        except APIError as exc:
            log.warning("WorldMonitor API error on %s: %s", tool, exc)
            if getattr(exc, "status", None) in (401, 403):
                raise GeoSourceError("WorldMonitor rejected the API key.") from exc
            raise GeoSourceError("WorldMonitor is unreachable right now.") from exc
        except OSError as exc:
            raise GeoSourceError("WorldMonitor is unreachable right now.") from exc
