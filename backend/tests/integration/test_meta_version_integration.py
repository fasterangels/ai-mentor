"""
Integration test: GET /api/v1/meta/version returns version from VERSION file.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

from main import app


def test_meta_version_returns_version() -> None:
    """GET /api/v1/meta/version returns JSON with version key."""
    client = TestClient(app)
    resp = client.get("/api/v1/meta/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) >= 1
