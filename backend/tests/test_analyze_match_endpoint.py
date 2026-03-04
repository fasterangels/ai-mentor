"""
Tests for POST /football/analyze_match: match info, analysis payload, unknown query error.
Deterministic; uses mock fixtures and mock providers when no env keys set.
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

ANALYSIS_KEYS = ["match", "lineups", "injuries", "last6", "h2h", "odds", "meta"]


def test_endpoint_returns_match_info() -> None:
    """POST /football/analyze_match with known query returns match info."""
    resp = client.post("/football/analyze_match", json={"query": "Arsenal Chelsea"})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" not in data
    assert "match" in data
    match = data["match"]
    assert match.get("match_id") == "M1"
    assert match.get("home") == "Arsenal"
    assert match.get("away") == "Chelsea"
    assert "league" in match
    assert "kickoff_iso" in match


def test_endpoint_returns_analysis_payload() -> None:
    """POST /football/analyze_match returns full analysis payload with required keys."""
    resp = client.post("/football/analyze_match", json={"query": "Arsenal Chelsea"})
    assert resp.status_code == 200
    data = resp.json()
    assert "analysis" in data
    analysis = data["analysis"]
    for key in ANALYSIS_KEYS:
        assert key in analysis
    assert "meta" in analysis
    assert "model_prediction" in analysis["meta"]
    assert "value_signal" in analysis["meta"]
    assert "decision" in analysis["meta"]


def test_unknown_query_returns_error() -> None:
    """POST /football/analyze_match with unknown query returns match_not_found."""
    resp = client.post("/football/analyze_match", json={"query": "Unknown Team XYZ"})
    assert resp.status_code == 200
    assert resp.json() == {"error": "match_not_found"}
