"""
Tests for injury impact layer: injury count, suspension count, availability, deterministic.
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

from backend.football.models import Injury
from backend.football.injury_impact import (
    InjuryImpact,
    build_injury_impact,
    compute_availability,
    compute_impact,
    compute_injury_counts,
)


def _inj(team_id: str, player: str, type_: str, status: str = "out") -> Injury:
    return Injury(team_id=team_id, player=player, type=type_, status=status)


def test_injury_count_correct() -> None:
    """Injury count is number of items with type 'injury' for the team."""
    injuries = [
        _inj("H", "P1", "injury"),
        _inj("H", "P2", "injury"),
        _inj("H", "P3", "suspension"),
        _inj("A", "P4", "injury"),
    ]
    result = build_injury_impact("H", injuries)
    assert result.injury_count == 2
    assert result.suspension_count == 1


def test_suspension_count_correct() -> None:
    """Suspension count is number of items with type 'suspension' for the team."""
    injuries = [
        _inj("T1", "P1", "suspension"),
        _inj("T1", "P2", "suspension"),
        _inj("T1", "P3", "injury"),
    ]
    ic, sc = compute_injury_counts([i for i in injuries if i.team_id == "T1"])
    assert ic == 1
    assert sc == 2


def test_availability_decreases_with_injuries() -> None:
    """Availability decreases as injury count increases; floored at 0.5."""
    assert compute_availability(0) == 1.0
    assert compute_availability(1) == 0.95
    assert compute_availability(10) == 0.5
    assert compute_availability(20) == 0.5

    zero = build_injury_impact("H", [])
    some = build_injury_impact("H", [_inj("H", "P1", "injury"), _inj("H", "P2", "injury")])
    assert some.availability < zero.availability


def test_deterministic_output() -> None:
    """Same inputs yield identical InjuryImpact."""
    injuries = [_inj("T1", "A", "injury"), _inj("T1", "B", "suspension")]
    a = build_injury_impact("T1", injuries)
    b = build_injury_impact("T1", injuries)
    assert a.injury_count == b.injury_count
    assert a.suspension_count == b.suspension_count
    assert a.injury_impact_score == b.injury_impact_score
    assert a.availability == b.availability
