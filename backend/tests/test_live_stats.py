"""
Tests for live match stats: default values, parsing, deterministic.
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

from backend.football.live_stats import LiveStats, build_live_stats


def test_default_values_when_fields_missing() -> None:
    """Missing fields get defaults: possession 50/50, counts 0, xG 0.0."""
    stats = build_live_stats({})
    assert stats.possession_home == 50
    assert stats.possession_away == 50
    assert stats.shots_home == 0
    assert stats.shots_away == 0
    assert stats.shots_on_target_home == 0
    assert stats.shots_on_target_away == 0
    assert stats.corners_home == 0
    assert stats.corners_away == 0
    assert stats.dangerous_attacks_home == 0
    assert stats.dangerous_attacks_away == 0
    assert stats.xg_home == 0.0
    assert stats.xg_away == 0.0


def test_correct_parsing_of_shots_and_possession() -> None:
    """Shots and possession parsed correctly from data."""
    data = {
        "possession_home": 65.5,
        "possession_away": 34.5,
        "shots_home": 12,
        "shots_away": 4,
        "shots_on_target_home": 5,
        "shots_on_target_away": 2,
        "xg_home": 1.8,
        "xg_away": 0.6,
    }
    stats = build_live_stats(data)
    assert stats.possession_home == 65.5
    assert stats.possession_away == 34.5
    assert stats.shots_home == 12
    assert stats.shots_away == 4
    assert stats.shots_on_target_home == 5
    assert stats.shots_on_target_away == 2
    assert stats.xg_home == 1.8
    assert stats.xg_away == 0.6


def test_deterministic_output() -> None:
    """Same input dict yields identical LiveStats."""
    data = {"possession_home": 60, "shots_home": 8, "xg_away": 0.9}
    a = build_live_stats(data)
    b = build_live_stats(data)
    assert a.possession_home == b.possession_home
    assert a.possession_away == b.possession_away
    assert a.shots_home == b.shots_home
    assert a.xg_away == b.xg_away
    assert a.__dict__ == b.__dict__
