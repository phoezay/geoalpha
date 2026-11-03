"""Background execution: runs belong to the server, not to the HTTP request (FR-006)."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor

from geoalpha.core.settings import Settings
from geoalpha.db import repo
from geoalpha.runner import events, orchestrator
from geoalpha.runner.orchestrator import Engine
from geoalpha.runner.registry import register_features

log = logging.getLogger(__name__)


def make_engine(settings: Settings) -> Engine:
    if settings.engine == "fake":
        from geoalpha.runner.fake_engine import FakeEngine

        return FakeEngine(step_delay_s=settings.fake_step_delay_s)
    from geoalpha.runner.ta_engine import TradingAgentsEngine

    return TradingAgentsEngine(settings)


class RunWorker:
    def __init__(self, settings: Settings, engine: Engine | None = None) -> None:
        self.settings = settings
        self.engine = engine or make_engine(settings)
        register_features(settings)
        self._pool = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_runs, thread_name_prefix="run"
        )

    def recover(self) -> None:
        """Runs left mid-flight by a previous process become `interrupted` (resumable)."""
        for run_id in repo.mark_running_as_interrupted():
            log.info("marked run %s interrupted after restart", run_id)
            events.publish(
                run_id,
                "run.finished",
                {"status": "interrupted", "error": "Server restarted during the run"},
            )

    def submit(self, run_id: str, *, resume: bool = False) -> Future[None]:
        return self._pool.submit(orchestrator.run_analysis, run_id, self.engine, resume=resume)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
