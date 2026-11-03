"""T023: every SSE payload of a full run validates against sse-events.schema.json."""

from __future__ import annotations

import json
from typing import Any

import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from tests.conftest import CONTRACTS, wait_for_run


def _validator() -> Draft202012Validator:
    schema = json.loads((CONTRACTS / "sse-events.schema.json").read_text(encoding="utf-8"))
    openapi = yaml.safe_load((CONTRACTS / "openapi.yaml").read_text(encoding="utf-8"))
    base = schema["$id"].rsplit("/", 1)[0]
    registry = Registry().with_resources(
        [
            (schema["$id"], Resource.from_contents(schema)),
            (f"{base}/openapi.yaml", DRAFT202012.create_resource(openapi)),
        ]
    )
    return Draft202012Validator(schema, registry=registry)


def _read_sse(client: TestClient, run_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        meta: dict[str, str] = {}
        for line in resp.iter_lines():
            if not line:
                if "data" in meta:
                    events.append(meta)
                meta = {}
                continue
            if line.startswith(":"):
                continue
            key, _, value = line.partition(":")
            meta[key] = value.strip()
        if "data" in meta:
            events.append(meta)
    return events


def test_full_run_events_match_schema(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"ticker": "XOM"}).json()["id"]
    wait_for_run(client, run_id)
    raw = _read_sse(client, run_id)
    assert raw, "no events"
    validator = _validator()
    seqs = []
    for msg in raw:
        payload = json.loads(msg["data"])
        errors = list(validator.iter_errors(payload))
        assert not errors, f"{payload['type']}: {errors[0].message}"
        assert msg["event"] == payload["type"]
        assert int(msg["id"]) == payload["seq"]
        seqs.append(payload["seq"])
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    types = [json.loads(m["data"])["type"] for m in raw]
    assert types[0] == "run.started" and types[-1] == "run.finished"
    assert "decision.ready" in types


def test_replay_after_last_event_id(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"ticker": "KO"}).json()["id"]
    wait_for_run(client, run_id)
    all_events = _read_sse(client, run_id)
    with client.stream("GET", f"/api/runs/{run_id}/events", headers={"Last-Event-ID": "5"}) as resp:
        ids = [int(line[3:]) for line in resp.iter_lines() if line.startswith("id:")]
    assert ids == [int(m["id"]) for m in all_events if int(m["id"]) > 5]
