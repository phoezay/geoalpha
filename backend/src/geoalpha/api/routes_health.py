from __future__ import annotations

from fastapi import APIRouter, Request

from geoalpha.api.schemas import Health
from geoalpha.core.settings import Settings

router = APIRouter()


@router.get("/api/health", operation_id="getHealth", response_model=Health)
def get_health(request: Request) -> Health:
    """Liveness plus configuration readiness (used to show config errors before a run)."""
    settings: Settings = request.app.state.settings
    return Health(
        ok=True,
        llm_configured=settings.llm_configured,
        llm_provider="offline demo" if settings.engine == "fake" else settings.llm_provider,
        geo_provider=settings.geo_provider,
        geo_configured=settings.geo_configured,
        forecast_model_ready=True,
        problems=settings.problems(),
    )
