from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from geoalpha.api.app import create_app
from geoalpha.core.settings import Settings
from geoalpha.runner.fake_engine import FakeEngine

SPEC_DIR = Path(__file__).resolve().parents[2] / "specs" / "001-geoalpha-mvp"
CONTRACTS = SPEC_DIR / "contracts"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        GEOALPHA_ENGINE="fake",
        GEOALPHA_GEO_PROVIDER="fixture",
        GEOALPHA_DATA_DIR=tmp_path,
        GEOALPHA_FAKE_STEP_DELAY_S=0.01,
        GEOALPHA_FAKE_FORECAST=True,
    )


@pytest.fixture
def client(settings: Settings, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(settings, engine=FakeEngine(step_delay_s=0.01), db_path=tmp_path / "t.db")
    with TestClient(app) as c:
        yield c


def wait_for_run(client: TestClient, run_id: str, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/api/runs/{run_id}").json()
        if body["status"] in ("completed", "failed", "interrupted"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not finish in {timeout}s")
