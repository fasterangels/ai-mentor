"""
Tests for football prediction model: probabilities sum to 1, form effect, deterministic.
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

from backend.football.prediction_model import (
    PredictionResult,
    build_prediction,
    normalize,
)


def _features(
    home_form: float = 0.5,
    home_momentum: float = 0.0,
    away_form: float = 0.5,
    away_momentum: float = 0.0,
    odds_home: float = 0.33,
    odds_draw: float = 0.33,
    odds_away: float = 0.34,
) -> dict:
    return {
        "meta": {
            "team_intelligence": {
                "home": {"form_score": home_form, "momentum": home_momentum},
                "away": {"form_score": away_form, "momentum": away_momentum},
            },
            "odds_intelligence": {
                "implied_probabilities": {
                    "home": odds_home,
                    "draw": odds_draw,
                    "away": odds_away,
                },
            },
        },
    }


def test_probabilities_sum_to_one() -> None:
    """Prediction home_prob + draw_prob + away_prob == 1.0."""
    features = _features()
    result = build_prediction(features)
    total = result.home_prob + result.draw_prob + result.away_prob
    assert abs(total - 1.0) < 1e-9


def test_stronger_home_form_increases_home_prob() -> None:
    """Higher home form_score (or momentum) increases home_prob."""
    weak = _features(home_form=0.2, away_form=0.6)
    strong = _features(home_form=0.8, away_form=0.2)
    r_weak = build_prediction(weak)
    r_strong = build_prediction(strong)
    assert r_strong.home_prob > r_weak.home_prob


def test_deterministic_result() -> None:
    """Same features dict yields identical PredictionResult."""
    features = _features(home_form=0.6, away_form=0.4, odds_home=0.4, odds_draw=0.3, odds_away=0.3)
    a = build_prediction(features)
    b = build_prediction(features)
    assert a.home_prob == b.home_prob
    assert a.draw_prob == b.draw_prob
    assert a.away_prob == b.away_prob
    assert a.model_score == b.model_score


def test_normalize_zero_sum() -> None:
    """normalize(0,0,0) returns (0.33, 0.33, 0.33)."""
    h, d, a = normalize(0.0, 0.0, 0.0)
    assert (h, d, a) == (0.33, 0.33, 0.33)


def test_normalize_positive() -> None:
    """normalize(1,1,1) returns (1/3, 1/3, 1/3)."""
    h, d, a = normalize(1.0, 1.0, 1.0)
    assert abs(h - 1.0 / 3) < 1e-9
    assert abs(d - 1.0 / 3) < 1e-9
    assert abs(a - 1.0 / 3) < 1e-9
