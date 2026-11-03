"""T084: history listing (FR-018)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import wait_for_run


def test_newest_first_with_cursor_pagination(client: TestClient) -> None:
    ids = [client.post("/api/runs", json={"ticker": t}).json()["id"] for t in ("XOM", "KO", "LMT")]
    for i in ids:
        wait_for_run(client, i)

    page1 = client.get("/api/runs", params={"limit": 2}).json()
    assert [r["id"] for r in page1["items"]] == [ids[2], ids[1]]
    assert page1["next_cursor"] == ids[1]

    page2 = client.get("/api/runs", params={"limit": 2, "cursor": page1["next_cursor"]}).json()
    assert [r["id"] for r in page2["items"]] == [ids[0]]
    assert page2["next_cursor"] is None


def test_rating_null_until_finished(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"ticker": "XOM"}).json()["id"]
    first = client.get("/api/runs", params={"limit": 1}).json()["items"][0]
    assert first["id"] == run_id
    if first["status"] != "completed":
        assert first["rating"] is None
    wait_for_run(client, run_id)
    done = client.get("/api/runs", params={"limit": 1}).json()["items"][0]
    assert done["rating"] == "Overweight" and done["finished_at"]


def test_limit_bounds(client: TestClient) -> None:
    assert client.get("/api/runs", params={"limit": 0}).status_code == 422
    assert client.get("/api/runs", params={"limit": 101}).status_code == 422
