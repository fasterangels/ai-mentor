"""
Tests for lineup strength layer: starters, missing players, strength vs injuries, deterministic.
Deterministic; no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo_root = _backend.parent
for _p in (_backend, _repo_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from backend.football.models import Injury, LineupPlayer
from backend.football.lineup_strength import (
    LineupStrength,
    build_lineup_strength,
    count_missing_players,
    count_players,
    compute_lineup_strength,
)


def _p(team_id: str, player: str, role: str) -> LineupPlayer:
    return LineupPlayer(team_id=team_id, player=player, role=role)


def _i(team_id: str, player: str, type_: str = "injury") -> Injury:
    return Injury(team_id=team_id, player=player, type=type_, status="out")


def test_starters_counted_correctly() -> None:
    """Starters and bench are counted per team_id and role."""
    lineup = [
        _p("H", "P1", "starter"),
        _p("H", "P2", "starter"),
        _p("H", "P3", "bench"),
        _p("A", "P4", "starter"),
    ]
    starters, bench = count_players(lineup, "H")
    assert starters == 2
    assert bench == 1

    result = build_lineup_strength("H", lineup, [])
    assert result.starters == 2
    assert result.bench_players == 1


def test_missing_players_counted() -> None:
    """Missing players = injuries (and suspensions) for the team."""
    injuries = [
        _i("T1", "X"),
        _i("T1", "Y"),
        _i("T2", "Z"),
    ]
    assert count_missing_players(injuries, "T1") == 2
    assert count_missing_players(injuries, "T2") == 1

    lineup = [_p("T1", "P1", "starter")]
    result = build_lineup_strength("T1", lineup, injuries)
    assert result.missing_players == 2


def test_lineup_strength_decreases_with_injuries() -> None:
    """More injuries for the team → lower lineup_strength_score."""
    lineup = [
        _p("T1", f"P{i}", "starter") for i in range(11)
    ] + [_p("T1", f"B{i}", "bench") for i in range(5)]
    no_injuries = build_lineup_strength("T1", lineup, [])
    with_injuries = build_lineup_strength("T1", lineup, [_i("T1", "X"), _i("T1", "Y")])
    assert with_injuries.lineup_strength_score < no_injuries.lineup_strength_score


def test_deterministic_output() -> None:
    """Same inputs yield identical LineupStrength."""
    lineup = [_p("T1", "A", "starter"), _p("T1", "B", "bench")]
    injuries = [_i("T1", "C")]
    a = build_lineup_strength("T1", lineup, injuries)
    b = build_lineup_strength("T1", lineup, injuries)
    assert a.starters == b.starters
    assert a.bench_players == b.bench_players
    assert a.missing_players == b.missing_players
    assert a.lineup_strength_score == b.lineup_strength_score
