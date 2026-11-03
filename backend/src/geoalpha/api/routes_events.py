from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Header
from sse_starlette.sse import EventSourceResponse

from geoalpha.db import repo
from geoalpha.runner import events

router = APIRouter()


@router.get(
    "/api/runs/{runId}/events",
    operation_id="streamRunEvents",
    response_class=EventSourceResponse,
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def stream_run_events(
    runId: str,  # noqa: N803 - path name fixed by the contract
    last_event_id: int | None = Header(default=None, alias="Last-Event-ID"),
) -> EventSourceResponse:
    """Server-Sent Events stream of run progress. Replays after Last-Event-ID, then live."""
    repo.get_run(runId)  # 404 before the stream starts

    async def gen() -> AsyncIterator[dict[str, Any]]:
        async for ev in events.subscribe(runId, last_event_id or 0):
            yield {"id": str(ev.seq), "event": ev.type, "data": json.dumps(ev.to_json())}

    return EventSourceResponse(gen(), ping=15)
