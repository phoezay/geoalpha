"""Run events: persisted first (so reconnecting clients can replay), then fanned out to
live SSE subscribers. `publish` is called from worker threads; subscribers live on the
server's event loop."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from geoalpha.db import repo


@dataclass(frozen=True)
class Event:
    seq: int
    run_id: str
    type: str
    at: datetime
    data: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "run_id": self.run_id,
            "type": self.type,
            "at": self.at.isoformat(),
            "data": self.data,
        }


_lock = threading.Lock()
# Serialises seq allocation (max+1) and fan-out: concurrent stages publish from different
# threads, and subscribers must receive events in seq order.
_publish_lock = threading.Lock()
_subscribers: dict[str, list[tuple[asyncio.AbstractEventLoop, asyncio.Queue[Event]]]] = {}


def publish(run_id: str, type_: str, data: dict[str, Any] | None = None) -> Event:
    payload = data or {}
    with _publish_lock:
        seq, at = repo.append_event(run_id, type_, payload)
        event = Event(seq=seq, run_id=run_id, type=type_, at=at, data=payload)
        with _lock:
            targets = list(_subscribers.get(run_id, ()))
        for loop, queue in targets:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:  # loop closed: subscriber is gone
                pass
    return event


async def subscribe(run_id: str, after_seq: int = 0) -> AsyncIterator[Event]:
    """Replay persisted events after `after_seq`, then stream live ones, in seq order
    without duplicates. Ends after `run.finished`."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Event] = asyncio.Queue()
    entry = (loop, queue)
    with _lock:
        _subscribers.setdefault(run_id, []).append(entry)
    try:
        last = after_seq
        for row in await asyncio.to_thread(repo.events_after, run_id, after_seq):
            ev = Event(row.seq, row.run_id, row.type, row.at.replace(tzinfo=UTC), row.data)
            last = ev.seq
            yield ev
            if ev.type == "run.finished":
                return
        while True:
            ev = await queue.get()
            if ev.seq <= last:
                continue
            last = ev.seq
            yield ev
            if ev.type == "run.finished":
                return
    finally:
        with _lock:
            subs = _subscribers.get(run_id, [])
            if entry in subs:
                subs.remove(entry)
            if not subs:
                _subscribers.pop(run_id, None)
