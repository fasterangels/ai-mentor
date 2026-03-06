"""
Tests for tactical signals: attacking strength, defensive weakness, goal expectation, deterministic.
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

from backend.football.models import H2HItem, LastMatch
from backend.football.tactical_signals import (
    TacticalSignals,
    build_tactical_signals,
    compute_attacking_strength,
    compute_defensive_weakness,
    compute_goal_expectation,
    compute_match_tempo,
)


def _last(team_id: str, opponent: str, result: str) -> LastMatch:
    return LastMatch(team_id=team_id, opponent=opponent, result=result, date_iso="2026-01-01T12:00:00Z")


def _h2h(home_goals: int, away_goals: int) -> H2HItem:
    return H2HItem(home_goals=home_goals, away_goals=away_goals, date_iso="2026-01-01T12:00:00Z")


def test_attacking_strength_positive_when_wins_present() -> None:
    """Attacking strength > 0 when wins (or draws) are present."""
    no_wins = [_last("T1", "A", "L"), _last("T1", "B", "L")]
    assert compute_attacking_strength(no_wins) == 0.0
    with_wins = [_last("T1", "A", "W"), _last("T1", "B", "D")]
    strength = compute_attacking_strength(with_wins)
    assert strength > 0.0
    assert strength == (1.0 + 0.5) / 2


def test_defensive_weakness_positive_when_losses_present() -> None:
    """Defensive weakness > 0 when losses are present."""
    no_losses = [_last("T1", "A", "W"), _last("T1", "B", "D")]
    assert compute_defensive_weakness(no_losses) == 0.0
    with_losses = [_last("T1", "A", "L"), _last("T1", "B", "W")]
    weakness = compute_defensive_weakness(with_losses)
    assert weakness > 0.0
    assert weakness == 0.5


def test_goal_expectation_equals_mean_goals() -> None:
    """Goal expectation is mean of total goals per H2H match; empty h2h returns 2.4."""
    assert compute_goal_expectation([]) == 2.4
    h2h = [_h2h(2, 1), _h2h(0, 3)]
    expect = compute_goal_expectation(h2h)
    assert expect == 3.0


def test_deterministic_output() -> None:
    """Same inputs yield identical TacticalSignals."""
    last_home = [_last("H", "A", "W"), _last("H", "B", "D")]
    last_away = [_last("A", "X", "L"), _last("A", "Y", "W")]
    h2h = [_h2h(1, 1), _h2h(2, 0)]
    a = build_tactical_signals(last_home, last_away, h2h)
    b = build_tactical_signals(last_home, last_away, h2h)
    assert a.attacking_strength == b.attacking_strength
    assert a.defensive_weakness == b.defensive_weakness
    assert a.goal_expectation == b.goal_expectation
    assert a.match_tempo == b.match_tempo
