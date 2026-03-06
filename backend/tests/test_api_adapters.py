"""
Tests for API-Football and Odds API adapters. No network: use handcrafted JSON and parsing helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football.adapters.api_football_adapter import (
    _parse_fixture,
    _parse_lineups,
    _parse_injuries,
    _parse_last_matches,
    _parse_h2h,
)
from backend.football.adapters.odds_api_adapter import parse_odds_response
from backend.football.models import MatchRef


def test_parse_fixture_returns_match_ref() -> None:
    """_parse_fixture maps API-Football fixture response to MatchRef."""
    payload = {
        "response": [
            {
                "fixture": {"id": 100, "date": "2026-02-01T15:00:00+00:00"},
                "league": {"name": "Premier League"},
                "teams": {
                    "home": {"id": 1, "name": "Home FC"},
                    "away": {"id": 2, "name": "Away FC"},
                },
                "goals": {"home": 2, "away": 1},
            }
        ]
    }
    result = _parse_fixture(payload)
    assert isinstance(result, MatchRef)
    assert result.match_id == "100"
    assert result.league == "Premier League"
    assert result.kickoff_iso == "2026-02-01T15:00:00+00:00"
    assert result.home.team_id == "1"
    assert result.home.name == "Home FC"
    assert result.away.team_id == "2"
    assert result.away.name == "Away FC"


def test_parse_lineups_returns_list() -> None:
    """_parse_lineups maps API-Football lineups response to list of LineupPlayer."""
    payload = {
        "response": [
            {
                "team": {"id": 1, "name": "Home FC"},
                "startXI": [{"player": {"id": 10, "name": "Player One"}}],
                "substitutes": [{"player": {"id": 11, "name": "Sub One"}}],
            }
        ]
    }
    result = _parse_lineups(payload)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].team_id == "1"
    assert result[0].player == "Player One"
    assert result[0].role == "starter"
    assert result[1].role == "bench"
    assert result[1].player == "Sub One"


def test_parse_injuries_returns_list() -> None:
    """_parse_injuries maps API-Football injuries response to list of Injury."""
    payload = {
        "response": [
            {"player": {"name": "John"}, "team": {"id": 1, "name": "Team A"}, "type": "injury"}
        ]
    }
    result = _parse_injuries(payload)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].team_id == "1"
    assert result[0].player == "John"
    assert result[0].status == "out"


def test_parse_last_matches_returns_w_d_l() -> None:
    """_parse_last_matches maps fixtures to LastMatch with W/D/L from goals."""
    payload = {
        "response": [
            {
                "fixture": {"id": 1, "date": "2026-01-01T12:00:00Z"},
                "teams": {"home": {"id": 10, "name": "Team"}, "away": {"id": 20, "name": "Opp"}},
                "goals": {"home": 2, "away": 1},
            },
            {
                "fixture": {"id": 2, "date": "2026-01-02T12:00:00Z"},
                "teams": {"home": {"id": 30, "name": "Other"}, "away": {"id": 10, "name": "Team"}},
                "goals": {"home": 0, "away": 0},
            },
        ]
    }
    result = _parse_last_matches(payload, "10")
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].team_id == "10"
    assert result[0].result == "W"
    assert result[0].date_iso == "2026-01-01T12:00:00Z"
    assert result[1].result == "D"


def test_parse_h2h_returns_items() -> None:
    """_parse_h2h maps headtohead response to list of H2HItem."""
    payload = {
        "response": [
            {
                "fixture": {"id": 1, "date": "2025-06-01T15:00:00Z"},
                "goals": {"home": 1, "away": 0},
            }
        ]
    }
    result = _parse_h2h(payload)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].home_goals == 1
    assert result[0].away_goals == 0
    assert "2025-06-01" in result[0].date_iso


def test_parse_odds_response_three_outcomes() -> None:
    """parse_odds_response returns 3 OddsQuote for h2h market (home/draw/away)."""
    payload = {
        "bookmakers": [
            {
                "key": "bm1",
                "title": "Bookmaker1",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Home", "price": 1.9},
                            {"name": "Draw", "price": 3.4},
                            {"name": "Away", "price": 4.1},
                        ],
                    }
                ],
            }
        ]
    }
    result = parse_odds_response(payload)
    assert len(result) == 3
    outcomes = {q.outcome for q in result}
    assert outcomes == {"home", "draw", "away"}
    assert all(q.market == "1x2" for q in result)
    assert result[0].price == 1.9
    assert result[1].price == 3.4
    assert result[2].price == 4.1


def test_parse_odds_response_allowlist_filter() -> None:
    """parse_odds_response filters by allowed_bookmakers when set."""
    payload = {
        "bookmakers": [
            {"key": "allowed_bm", "title": "Allowed", "markets": [{"key": "h2h", "outcomes": [{"name": "A", "price": 2.0}, {"name": "B", "price": 3.0}]}]},
            {"key": "other_bm", "title": "Other", "markets": [{"key": "h2h", "outcomes": [{"name": "A", "price": 1.9}, {"name": "B", "price": 3.1}]}]},
        ]
    }
    result_all = parse_odds_response(payload, allowed_bookmakers=None)
    result_filtered = parse_odds_response(payload, allowed_bookmakers={"allowed_bm"})
    assert len(result_all) == 4
    assert len(result_filtered) == 2
    assert all(q.bookmaker == "Allowed" for q in result_filtered)
