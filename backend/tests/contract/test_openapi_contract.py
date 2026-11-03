"""T022: the served OpenAPI document matches contracts/openapi.yaml."""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from tests.conftest import CONTRACTS

# Endpoints delivered by later stories (US5 export) are not served yet.
NOT_YET_IMPLEMENTED: set[tuple[str, str]] = set()


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    return yaml.safe_load((CONTRACTS / "openapi.yaml").read_text(encoding="utf-8"))


def _operations(doc: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (path, method): op
        for path, item in doc["paths"].items()
        for method, op in item.items()
        if method in ("get", "post", "put", "patch", "delete")
    }


def test_every_contract_operation_is_served(client: TestClient, contract: dict[str, Any]) -> None:
    served = _operations(client.get("/openapi.json").json())
    for key, op in _operations(contract).items():
        if key in NOT_YET_IMPLEMENTED:
            continue
        assert key in served, f"missing {key}"
        assert served[key]["operationId"] == op["operationId"]


def _resolve(doc: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        schema = doc["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def _props(doc: dict[str, Any], name: str) -> tuple[set[str], dict[str, Any]]:
    schema = doc["components"]["schemas"][name]
    required: set[str] = set(schema.get("required", []))
    props: dict[str, Any] = dict(schema.get("properties", {}))
    for part in schema.get("allOf", []):
        part = _resolve(doc, part)
        required |= set(part.get("required", []))
        props.update(part.get("properties", {}))
    return required, props


def _enum(doc: dict[str, Any], schema: dict[str, Any]) -> set[Any] | None:
    schema = _resolve(doc, schema)
    for variant in [schema, *schema.get("anyOf", []), *schema.get("oneOf", [])]:
        variant = _resolve(doc, variant)
        if "enum" in variant:
            return {v for v in variant["enum"] if v is not None}
    return None


@pytest.mark.parametrize(
    "name",
    [
        "Health",
        "TickerValidation",
        "Stage",
        "GeoSignal",
        "GeoSummary",
        "PriceForecast",
        "Decision",
        "RunSummary",
        "RunPage",
        "RunDetail",
    ],
)
def test_component_schemas_match(client: TestClient, contract: dict[str, Any], name: str) -> None:
    served = client.get("/openapi.json").json()
    c_req, c_props = _props(contract, name)
    s_req, s_props = _props(served, name)
    assert set(c_props) == set(s_props), f"{name} fields differ"
    assert c_req <= s_req | {k for k in c_props if "default" in s_props.get(k, {})}, name
    for field, c_schema in c_props.items():
        c_enum = _enum(contract, c_schema)
        if c_enum is not None:
            assert _enum(served, s_props[field]) == c_enum, f"{name}.{field} enum differs"
