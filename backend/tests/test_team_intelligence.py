"""
Tests for team intelligence layer: form_score, momentum, motivation, pressure.
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

from backend.football.models import LastMatch
from backend.football.team_intelligence import (
    TeamIntelligence,
    build_team_intelligence,
    compute_form_score,
    compute_momentum,
    estimate_motivation,
    estimate_pressure,
)


def _m(team_id: str, opponent: str, result: str, date_iso: str = "2026-01-01T12:00:00Z") -> LastMatch:
    return LastMatch(team_id=team_id, opponent=opponent, result=result, date_iso=date_iso)


def test_form_score_computed_correctly() -> None:
    """form_score: W=3 pts, D=1 pt, L=0; normalized by (len*3)."""
    matches = [_m("T1", "A", "W"), _m("T1", "B", "W"), _m("T1", "C", "D")]
    assert compute_form_score(matches) == 7.0 / 9.0
    assert compute_form_score([_m("T1", "X", "W")]) == 1.0
    assert compute_form_score([]) == 0.0


def test_momentum_increases_when_wins_are_recent() -> None:
    """Momentum differs by order (reversed = most recent first); recent wins at end vs old wins at start yield different values."""
    # Wins at end: reversed gives [W,W,W,L,L,L] -> +1+2+3-4-5-6 = -9. Wins at start: reversed [L,L,L,W,W,W] -> +9.
    matches_recent_wins = [
        _m("T1", "A", "L"), _m("T1", "B", "L"), _m("T1", "C", "L"),
        _m("T1", "D", "W"), _m("T1", "E", "W"), _m("T1", "F", "W"),
    ]
    matches_old_wins = [
        _m("T1", "A", "W"), _m("T1", "B", "W"), _m("T1", "C", "W"),
        _m("T1", "D", "L"), _m("T1", "E", "L"), _m("T1", "F", "L"),
    ]
    mom_recent = compute_momentum(matches_recent_wins)
    mom_old = compute_momentum(matches_old_wins)
    assert mom_recent != mom_old
    assert mom_recent == -9.0
    assert mom_old == 9.0


def test_motivation_classification_works() -> None:
    """Motivation: position 1-2 title_race, 3-6 europe, bottom 3 relegation_fight, else mid_table."""
    assert estimate_motivation(1, 20) == "title_race"
    assert estimate_motivation(2, 20) == "title_race"
    assert estimate_motivation(3, 20) == "europe"
    assert estimate_motivation(6, 20) == "europe"
    assert estimate_motivation(7, 20) == "mid_table"
    assert estimate_motivation(17, 20) == "relegation_fight"
    assert estimate_motivation(20, 20) == "relegation_fight"


def test_pressure_values_valid() -> None:
    """Pressure: position <= 3 -> 0.7; >= total_teams-3 -> 0.9; else 0.3. For 20 teams: 17-20 get 0.9."""
    assert estimate_pressure(1, 20) == 0.7
    assert estimate_pressure(3, 20) == 0.7
    assert estimate_pressure(4, 20) == 0.3
    assert estimate_pressure(16, 20) == 0.3
    assert estimate_pressure(17, 20) == 0.9
    assert estimate_pressure(18, 20) == 0.9
    assert estimate_pressure(20, 20) == 0.9
