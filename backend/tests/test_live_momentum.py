"""
Tests for live momentum engine: home pressure, balanced, deterministic.
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

from backend.football.live_stats import LiveStats
from backend.football.live_momentum import LiveMomentum, build_live_momentum


def test_momentum_detected_for_home_pressure() -> None:
    """Higher home attacking pressure yields momentum_team 'home'."""
    stats = LiveStats(
        possession_home=60.0,
        possession_away=40.0,
        shots_home=10,
        shots_away=2,
        shots_on_target_home=5,
        shots_on_target_away=1,
        corners_home=6,
        corners_away=2,
        dangerous_attacks_home=20,
        dangerous_attacks_away=5,
        xg_home=1.5,
        xg_away=0.3,
    )
    momentum = build_live_momentum(stats)
    assert momentum.momentum_team == "home"
    assert momentum.attacking_pressure_home > momentum.attacking_pressure_away
    assert momentum.momentum_strength > 0


def test_balanced_when_equal_stats() -> None:
    """Equal pressure on both sides yields momentum_team 'balanced'."""
    stats = LiveStats(
        possession_home=50.0,
        possession_away=50.0,
        shots_home=5,
        shots_away=5,
        shots_on_target_home=2,
        shots_on_target_away=2,
        corners_home=3,
        corners_away=3,
        dangerous_attacks_home=10,
        dangerous_attacks_away=10,
        xg_home=0.8,
        xg_away=0.8,
    )
    momentum = build_live_momentum(stats)
    assert momentum.momentum_team == "balanced"
    assert momentum.momentum_strength == 0.0


def test_deterministic_output() -> None:
    """Same LiveStats yields identical LiveMomentum."""
    stats = LiveStats(
        possession_home=55.0,
        possession_away=45.0,
        shots_home=8,
        shots_away=4,
        shots_on_target_home=4,
        shots_on_target_away=2,
        corners_home=5,
        corners_away=3,
        dangerous_attacks_home=15,
        dangerous_attacks_away=8,
        xg_home=1.2,
        xg_away=0.6,
    )
    a = build_live_momentum(stats)
    b = build_live_momentum(stats)
    assert a.attacking_pressure_home == b.attacking_pressure_home
    assert a.attacking_pressure_away == b.attacking_pressure_away
    assert a.control_index_home == b.control_index_home
    assert a.control_index_away == b.control_index_away
    assert a.momentum_team == b.momentum_team
    assert a.momentum_strength == b.momentum_strength
    assert a.__dict__ == b.__dict__
