"""T034: run creation input rules (FR-001, FR-002, edge cases)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from geoalpha.core import market_calendar


def test_ticker_uppercased_and_default_date(client: TestClient) -> None:
    resp = client.post("/api/runs", json={"ticker": "xom"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["ticker"] == "XOM"
    assert body["requested_date"] == market_calendar.last_completed_session().isoformat()
    assert len(body["stages"]) == 10
    assert body["last_event_seq"] >= 0


def test_future_date_rejected(client: TestClient) -> None:
    future = (market_calendar.today_et() + timedelta(days=3)).isoformat()
    resp = client.post("/api/runs", json={"ticker": "XOM", "date": future})
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert "date" in resp.json()["field_errors"]


def test_bad_ticker_pattern_rejected(client: TestClient) -> None:
    resp = client.post("/api/runs", json={"ticker": "1BAD"})
    assert resp.status_code == 422
    assert "ticker" in resp.json()["field_errors"]


def test_weekend_rolls_back_to_friday(client: TestClient) -> None:
    saturday = date(2026, 10, 31)
    resp = client.post("/api/runs", json={"ticker": "XOM", "date": saturday.isoformat()})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["requested_date"] == "2026-10-31"
    assert body["analysis_date"] == "2026-10-30"


def test_holiday_rolls_back() -> None:
    assert market_calendar.roll_back_to_session(date(2026, 12, 25)) == date(2026, 12, 24)


def test_unknown_run_is_404_problem(client: TestClient) -> None:
    resp = client.get("/api/runs/01JDOESNOTEXIST0000000000")
    assert resp.status_code == 404
    assert resp.json()["status"] == 404
