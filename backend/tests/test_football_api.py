"""
Tests for football feature builder API: GET /football/demo_match, POST /football/features.
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

REQUIRED_KEYS = ["match", "lineups", "injuries", "last6", "h2h", "odds", "meta"]


def test_get_demo_match_returns_required_keys() -> None:
    """GET /football/demo_match returns payload with all required keys."""
    resp = client.get("/football/demo_match")
    assert resp.status_code == 200
    data = resp.json()
    for key in REQUIRED_KEYS:
        assert key in data


def test_post_football_features_with_match_id() -> None:
    """POST /football/features with match_id returns full features payload."""
    resp = client.post("/football/features", json={"match_id": "X"})
    assert resp.status_code == 200
    data = resp.json()
    for key in REQUIRED_KEYS:
        assert key in data
    assert data["match"].get("match_id") == "X" or data["match"].get("league") == "DEMO"


def test_post_football_features_missing_match_id() -> None:
    """POST /football/features with missing/empty match_id returns error."""
    resp = client.post("/football/features", json={})
    assert resp.status_code == 200
    assert resp.json() == {"error": "missing_match_id"}

    resp2 = client.post("/football/features", json={"match_id": ""})
    assert resp2.status_code == 200
    assert resp2.json() == {"error": "missing_match_id"}


def test_last6_has_two_teams_each_list_max_six() -> None:
    """last6 contains exactly 2 teams and each list length <= 6."""
    resp = client.get("/football/demo_match")
    assert resp.status_code == 200
    data = resp.json()
    last6 = data["last6"]
    assert isinstance(last6, dict)
    assert len(last6) == 2
    for team_id, matches in last6.items():
        assert isinstance(matches, list)
        assert len(matches) <= 6


def test_demo_match_deterministic() -> None:
    """Calling GET /football/demo_match twice yields identical JSON."""
    resp1 = client.get("/football/demo_match")
    resp2 = client.get("/football/demo_match")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
