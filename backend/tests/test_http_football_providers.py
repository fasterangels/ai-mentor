"""
Tests for HTTP JSON football providers. No network: monkeypatch urlopen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football.http_providers import (
    HttpJsonFootballOddsProvider,
    HttpJsonFootballStatsProvider,
)
from backend.football.models import MatchRef, OddsQuote


def _mock_response(json_body: Dict[str, Any] | list) -> MagicMock:
    raw = json.dumps(json_body).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = raw
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=None)
    return resp


def test_http_stats_get_match_returns_match_ref(monkeypatch: Any) -> None:
    """get_match returns MatchRef with expected ids/names when urlopen returns normalized JSON."""
    match_payload = {
        "match_id": "M1",
        "league": "LEAGUE_X",
        "kickoff_iso": "2026-02-01T15:00:00Z",
        "home": {"team_id": "T_HOME", "name": "Home Team"},
        "away": {"team_id": "T_AWAY", "name": "Away Team"},
    }

    def fake_urlopen(req: Any, timeout: int = 10) -> MagicMock:
        return _mock_response(match_payload)

    monkeypatch.setattr(
        "backend.football.http_providers.urlopen",
        fake_urlopen,
    )

    provider = HttpJsonFootballStatsProvider("https://api.example.com")
    result = provider.get_match("M1")

    assert isinstance(result, MatchRef)
    assert result.match_id == "M1"
    assert result.league == "LEAGUE_X"
    assert result.home.team_id == "T_HOME"
    assert result.home.name == "Home Team"
    assert result.away.team_id == "T_AWAY"
    assert result.away.name == "Away Team"


def test_http_odds_get_odds_returns_three_quotes(monkeypatch: Any) -> None:
    """get_odds returns 3 OddsQuote when urlopen returns odds array."""
    odds_payload = {
        "odds": [
            {"bookmaker": "B1", "market": "1x2", "outcome": "home", "price": 1.9},
            {"bookmaker": "B1", "market": "1x2", "outcome": "draw", "price": 3.4},
            {"bookmaker": "B1", "market": "1x2", "outcome": "away", "price": 4.1},
        ]
    }

    def fake_urlopen(req: Any, timeout: int = 10) -> MagicMock:
        return _mock_response(odds_payload)

    monkeypatch.setattr(
        "backend.football.http_providers.urlopen",
        fake_urlopen,
    )

    provider = HttpJsonFootballOddsProvider("https://odds.example.com")
    result = provider.get_odds("M1")

    assert len(result) == 3
    for q in result:
        assert isinstance(q, OddsQuote)
    assert result[0].outcome == "home"
    assert result[1].outcome == "draw"
    assert result[2].outcome == "away"


def test_health_returns_status_and_football_provider_names() -> None:
    """GET /health returns status and football_stats_provider, football_odds_provider (no network)."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "football_stats_provider" in data
    assert "football_odds_provider" in data
    # Default (no env) is mock providers
    assert data["football_stats_provider"] == "mock_stats"
    assert data["football_odds_provider"] == "mock_odds"
