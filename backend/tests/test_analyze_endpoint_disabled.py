"""
Phase A: /api/v1/analyze is disabled by design (501, hidden from OpenAPI).
Contract: exact error payload; endpoint excluded from Swagger.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

from main import app


def test_analyze_returns_501() -> None:
    """POST /api/v1/analyze always returns HTTP 501."""
    client = TestClient(app)
    resp = client.post("/api/v1/analyze", json={})
    assert resp.status_code == 501


def test_analyze_501_payload_contract() -> None:
    """501 response body matches exact contract: error.code, message, remediation.endpoint."""
    client = TestClient(app)
    resp = client.post("/api/v1/analyze", json={})
    assert resp.status_code == 501
    data = resp.json()
    assert "error" in data
    err = data["error"]
    assert err.get("code") == "ANALYZE_ENDPOINT_NOT_SUPPORTED"
    assert "/pipeline/shadow/run" in (err.get("message") or "")
    assert "remediation" in err
    assert err["remediation"].get("endpoint") == "/pipeline/shadow/run"
    assert "notes" in err["remediation"]


def test_analyze_excluded_from_openapi() -> None:
    """OpenAPI schema must not expose /api/v1/analyze (hidden from Swagger)."""
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    openapi = resp.json()
    paths = openapi.get("paths") or {}
    assert "/api/v1/analyze" not in paths
