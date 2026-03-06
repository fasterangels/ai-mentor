"""
Tests for football match finder: find_match_by_teams, find_matches_by_team.
Deterministic; uses mock fixtures only.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football.match_finder import (
    TeamMatch,
    find_match_by_teams,
    find_matches_by_team,
)
from backend.football.mock_fixtures import get_mock_fixtures


def test_find_match_by_teams_finds_arsenal_vs_chelsea() -> None:
    """find_match_by_teams finds Arsenal vs Chelsea."""
    fixtures = get_mock_fixtures()
    match = find_match_by_teams("Arsenal vs Chelsea", fixtures)
    assert match is not None
    assert match.match_id == "M1"
    assert match.home == "Arsenal"
    assert match.away == "Chelsea"
    assert match.league == "Premier League"
    assert match.kickoff_iso == "2026-01-01T18:00:00Z"


def test_find_match_by_teams_accepts_arbitrary_query() -> None:
    """Query 'Arsenal Chelsea' (no 'vs') also finds the match."""
    fixtures = get_mock_fixtures()
    match = find_match_by_teams("Arsenal Chelsea", fixtures)
    assert match is not None
    assert match.match_id == "M1"


def test_find_matches_by_team_barcelona_returns_one_match() -> None:
    """find_matches_by_team('Barcelona') returns one match."""
    fixtures = get_mock_fixtures()
    matches = find_matches_by_team("Barcelona", fixtures)
    assert len(matches) == 1
    assert matches[0].match_id == "M2"
    assert matches[0].home == "Barcelona"
    assert matches[0].away == "Real Madrid"


def test_unknown_query_returns_none() -> None:
    """Unknown query returns None."""
    fixtures = get_mock_fixtures()
    match = find_match_by_teams("Unknown Team vs Other", fixtures)
    assert match is None
