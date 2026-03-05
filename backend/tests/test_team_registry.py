from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from services.team_registry import load_teams, load_leagues, resolve_team, resolve_league  # noqa: E402


def test_team_alias_resolution_works():
    teams = load_teams()
    assert teams, "teams.json should contain at least one team"

    # Main name
    t1 = resolve_team("Manchester United")
    assert t1 is not None
    assert t1["id"] == "manchester_united"

    # Alias resolution
    t2 = resolve_team("Man United")
    assert t2 is not None
    assert t2["id"] == "manchester_united"

    t3 = resolve_team("Manchester Utd")
    assert t3 is not None
    assert t3["id"] == "manchester_united"


def test_unknown_team_handled_safely():
    assert resolve_team("Some Nonexistent FC") is None
    assert resolve_team("") is None
    assert resolve_team("   ") is None


def test_league_resolution_by_name_and_id():
    leagues = load_leagues()
    assert leagues, "leagues.json should contain at least one league"

    l1 = resolve_league("Premier League")
    assert l1 is not None
    assert l1["id"] == "premier_league"

    l2 = resolve_league("premier_league")
    assert l2 is not None
    assert l2["id"] == "premier_league"

