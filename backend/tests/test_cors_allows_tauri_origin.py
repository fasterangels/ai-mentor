"""
Test CORS: OPTIONS preflight for Tauri desktop origin must return Access-Control-* headers
so the webview can call the local backend API (e.g. POST /api/v1/pipeline/shadow/run).

Run from repo root: python -m pytest backend/tests/test_cors_allows_tauri_origin.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_cors_preflight_tauri_origin_returns_allow_headers() -> None:
    """OPTIONS /api/v1/pipeline/shadow/run with Origin: tauri://localhost returns CORS headers."""
    resp = client.options(
        "/api/v1/pipeline/shadow/run",
        headers={
            "Origin": "tauri://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Preflight may be 200 or 204; CORS middleware sets headers either way
    assert resp.status_code in (200, 204)

    headers = {k.lower(): v for k, v in resp.headers.items()}
    assert "access-control-allow-origin" in headers
    allow_origin = headers["access-control-allow-origin"]
    assert allow_origin == "tauri://localhost" or allow_origin == "*"

    assert "access-control-allow-methods" in headers
    allow_methods = headers["access-control-allow-methods"]
    assert "POST" in allow_methods or "*" in allow_methods
