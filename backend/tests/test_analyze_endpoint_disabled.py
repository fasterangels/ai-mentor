"""
Phase A / A.2: /api/v1/analyze disabled by design (501, hidden from OpenAPI).
Enforcement: exact 501 payload contract; endpoint excluded from OpenAPI schema.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from fastapi.testclient import TestClient

from main import app

# Exact 501 contract (deterministic, no timestamps/ids). Enforced by tests.
EXACT_501_PAYLOAD = {
    "error": {
        "code": "ANALYZE_ENDPOINT_NOT_SUPPORTED",
        "message": "This endpoint is intentionally not supported. Use /pipeline/shadow/run.",
        "remediation": {
            "endpoint": "/pipeline/shadow/run",
            "notes": "The analyzer is designed to run inside the pipeline execution model.",
        },
    },
}


def test_analyze_returns_501_and_contract() -> None:
    """POST /api/v1/analyze returns 501 with exact deterministic payload (any/empty body)."""
    client = TestClient(app)
    resp = client.post("/api/v1/analyze", json={})
    assert resp.status_code == 501
    assert resp.json() == EXACT_501_PAYLOAD


def test_openapi_does_not_expose_analyze() -> None:
    """OpenAPI schema must not expose /api/v1/analyze (hidden from Swagger)."""
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/v1/analyze" not in (schema.get("paths") or {})
