"""
Tests for live probability update: probs sum to 1, home momentum increases home_prob, deterministic.
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

from backend.football.live_probability import LiveProbability, update_live_probability


def test_probabilities_sum_to_one() -> None:
    """Updated live probabilities sum to 1.0."""
    pre_match = {"home_prob": 0.4, "draw_prob": 0.3, "away_prob": 0.3}
    momentum = {"momentum_team": "home", "momentum_strength": 0.5}
    stats = {"shots_home": 8, "shots_away": 4}
    result = update_live_probability(pre_match, momentum, stats)
    total = result.home_prob + result.draw_prob + result.away_prob
    assert abs(total - 1.0) < 1e-9


def test_home_momentum_increases_home_probability() -> None:
    """Home momentum yields higher home_prob than balanced momentum (same pre_match and stats)."""
    pre_match = {"home_prob": 0.35, "draw_prob": 0.3, "away_prob": 0.35}
    stats = {"shots_home": 5, "shots_away": 5}
    balanced = update_live_probability(
        pre_match,
        {"momentum_team": "balanced", "momentum_strength": 0.0},
        stats,
    )
    home_momentum = update_live_probability(
        pre_match,
        {"momentum_team": "home", "momentum_strength": 1.0},
        stats,
    )
    assert home_momentum.home_prob > balanced.home_prob
    assert home_momentum.away_prob < balanced.away_prob


def test_deterministic_output() -> None:
    """Same inputs yield identical LiveProbability."""
    pre_match = {"home_prob": 0.4, "draw_prob": 0.3, "away_prob": 0.3}
    momentum = {"momentum_team": "away", "momentum_strength": 0.3}
    stats = {"shots_home": 3, "shots_away": 7}
    a = update_live_probability(pre_match, momentum, stats)
    b = update_live_probability(pre_match, momentum, stats)
    assert a.home_prob == b.home_prob
    assert a.draw_prob == b.draw_prob
    assert a.away_prob == b.away_prob
    assert a.__dict__ == b.__dict__
