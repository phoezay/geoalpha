"""T090: report export (FR-025)."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from tests.conftest import wait_for_run


def _completed(client: TestClient, ticker: str = "XOM") -> dict:
    run_id = client.post("/api/runs", json={"ticker": ticker}).json()["id"]
    return wait_for_run(client, run_id)


def test_markdown_contains_every_section(client: TestClient) -> None:
    run = _completed(client)
    resp = client.get(f"/api/runs/{run['id']}/export", params={"format": "md"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    expected = f"{run['ticker']}_{run['analysis_date']}_{run['id']}.md"
    assert f'filename="{expected}"' in resp.headers["content-disposition"]
    text = resp.text
    for needle in (
        "## Decision",
        "Rating: Overweight",
        "confidence",
        "## Geopolitical signals",
        "## Price forecast",
        "Expected move",
        "### Market",
        "### Sentiment",
        "### News",
        "### Fundamentals",
        "## Bull vs Bear debate",
        "## Trader & risk review",
        "Research output, not financial advice.",
        run["deep_model"],
        run["geo"]["signals"][0]["source_label"].split(" · ")[0],
    ):
        assert needle in text, needle


def test_html_is_self_contained_and_escapes_model_html(client: TestClient) -> None:
    run = _completed(client)
    resp = client.get(f"/api/runs/{run['id']}/export", params={"format": "html"})
    assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/html")
    page = resp.text
    assert page.startswith("<!doctype html>") and "<svg" in page
    assert "<script" not in page
    # No external resources other than plain source links.
    assert not re.search(r'<(img|link|script|iframe)[^>]+(src|href)="https?://', page)
    for needle in (
        "Decision",
        "Geopolitical signals",
        "Price forecast",
        "Analyst reports",
        "Research output, not financial advice.",
    ):
        assert needle in page


def test_unfinished_run_conflicts_and_bad_format_rejected(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"ticker": "FAILME"}).json()["id"]
    wait_for_run(client, run_id)  # fails at the trader stage
    assert client.get(f"/api/runs/{run_id}/export", params={"format": "md"}).status_code == 409
    assert client.get(f"/api/runs/{run_id}/export", params={"format": "pdf"}).status_code == 422


def test_model_html_is_escaped() -> None:
    from geoalpha.api.export import _md

    assert "<script>" not in _md.render("hello <script>alert(1)</script>")
