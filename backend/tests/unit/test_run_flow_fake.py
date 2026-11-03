"""T036: end-to-end run lifecycle with the scripted engine."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import wait_for_run


def test_full_run_completes_with_decision(client: TestClient) -> None:
    created = client.post("/api/runs", json={"ticker": "XOM"})
    assert created.status_code == 201
    body = created.json()
    assert [s["key"] for s in body["stages"]] == [
        "geo",
        "forecast",
        "market",
        "sentiment",
        "news",
        "fundamentals",
        "research_debate",
        "trader",
        "risk_debate",
        "decision",
    ]

    final = wait_for_run(client, body["id"])
    assert final["status"] == "completed", final.get("error")
    statuses = {s["key"]: s["status"] for s in final["stages"]}
    assert all(statuses[k] == "done" for k in statuses)
    geo = final["geo"]
    assert geo["materiality"] == "material" and 1 <= len(geo["signals"]) <= 10
    assert [s["rank"] for s in geo["signals"]] == list(range(1, len(geo["signals"]) + 1))
    assert all(s["source_label"] and s["valid_at"] for s in geo["signals"])
    assert final["decision"]["geo_statement"] == "cites"
    assert set(final["decision"]["cited_signal_ids"]) <= {s["id"] for s in geo["signals"]}
    assert final["forecast"]["horizon"] == 5 and len(final["forecast"]["path"]) == 5
    assert final["decision"]["forecast_alignment"] in ("supports", "contradicts", "neutral")
    assert final["decision"]["rating"] == "Overweight"
    assert final["decision"]["disclaimer"] == "Research output, not financial advice."
    assert final["llm_provider"] and final["deep_model"]
    debate = next(s for s in final["stages"] if s["key"] == "research_debate")
    assert set(debate["payload"]) == {"bull_history", "bear_history", "judge"}
    assert final["rating"] == "Overweight"


def test_failed_run_resumes_from_failed_stage(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"ticker": "FAILME"}).json()["id"]
    failed = wait_for_run(client, run_id)
    assert failed["status"] == "failed"
    stages = {s["key"]: s for s in failed["stages"]}
    assert stages["trader"]["status"] == "failed"
    assert stages["research_debate"]["status"] == "done"

    assert client.post(f"/api/runs/{run_id}/retry", json={"mode": "resume"}).status_code == 202
    resumed = wait_for_run(client, run_id)
    assert resumed["status"] == "completed"
    stages = {s["key"]: s for s in resumed["stages"]}
    assert stages["trader"]["attempts"] == 2
    assert stages["market"]["attempts"] == 1  # completed stages were not re-run


def test_resume_completed_run_conflicts_and_fresh_links(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"ticker": "KO"}).json()["id"]
    wait_for_run(client, run_id)
    assert client.post(f"/api/runs/{run_id}/retry", json={"mode": "resume"}).status_code == 409
    fresh = client.post(f"/api/runs/{run_id}/retry", json={"mode": "fresh"})
    assert fresh.status_code == 202
    assert fresh.json()["retry_of"] == run_id and fresh.json()["id"] != run_id


def test_config_problem_blocks_run(client: TestClient) -> None:
    client.app.state.settings.engine = "tradingagents"  # type: ignore[attr-defined]
    client.app.state.settings.llm_provider = "anthropic"  # type: ignore[attr-defined]
    import os

    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        resp = client.post("/api/runs", json={"ticker": "XOM"})
        assert resp.status_code == 503
        assert "ANTHROPIC_API_KEY" in resp.json()["detail"]
        health = client.get("/api/health").json()
        assert health["llm_configured"] is False and health["problems"]
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
        client.app.state.settings.engine = "fake"  # type: ignore[attr-defined]


def test_list_runs_newest_first(client: TestClient) -> None:
    a = client.post("/api/runs", json={"ticker": "XOM"}).json()["id"]
    b = client.post("/api/runs", json={"ticker": "KO"}).json()["id"]
    wait_for_run(client, a)
    wait_for_run(client, b)
    items = client.get("/api/runs").json()["items"]
    assert [i["id"] for i in items[:2]] == [b, a]


def test_short_history_forecast_is_unavailable_not_failed(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"ticker": "NEWIPO"}).json()["id"]
    final = wait_for_run(client, run_id)
    assert final["status"] == "completed"
    forecast = next(s for s in final["stages"] if s["key"] == "forecast")
    assert forecast["status"] == "unavailable"
    assert "Not enough price history" in forecast["error"]
    assert final["forecast"] is None
    assert final["missing_inputs"] == ["forecast"]
    assert final["decision"]["forecast_alignment"] == "unavailable"
    assert final["decision"]["confidence"] != "high"
