"""
Tests for data source API: GET /sources, POST /fetch, and caching.
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
from sources.cache import cache_key

client = TestClient(app)


def test_sources_returns_mock() -> None:
    """GET /sources returns list including mock source."""
    resp = client.get("/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert "mock" in data["sources"]


def test_fetch_mock_returns_payload() -> None:
    """POST /fetch with mock source returns payload."""
    resp = client.post("/fetch", json={"source": "mock", "market": "demo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "mock"
    assert data["market"] == "demo"
    assert "payload" in data
    payload = data["payload"]
    assert payload.get("market") == "demo"
    assert payload.get("note") == "mock"
    assert "items" in payload


def test_fetch_cache_behavior() -> None:
    """First fetch: cached False; second fetch same source/market: cached True."""
    source, market = "mock", "test_cache_market"
    path = cache_key(source, market)
    if path.exists():
        path.unlink()

    resp1 = client.post("/fetch", json={"source": source, "market": market})
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["cached"] is False
    assert d1["source"] == source
    assert d1["market"] == market
    assert "payload" in d1

    resp2 = client.post("/fetch", json={"source": source, "market": market})
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["cached"] is True
    assert d2["payload"] == d1["payload"]
