"""
Tests for value/edge detector: edge sign, is_value threshold, reason codes.
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

from backend.football import value_detector


def test_edge_positive_when_model_gt_implied():
    """Edge for an outcome is positive when model probability exceeds implied."""
    model_probs = {"home_prob": 0.50, "draw_prob": 0.30, "away_prob": 0.20}
    implied_probs = {"home": 0.40, "draw": 0.35, "away": 0.25}
    v = value_detector.compute_edges(model_probs, implied_probs)
    assert abs(v.edge_home - 0.10) < 1e-9
    assert abs(v.edge_draw - (-0.05)) < 1e-9
    assert abs(v.edge_away - (-0.05)) < 1e-9
    assert v.best_outcome == "home"
    assert abs(v.best_edge - 0.10) < 1e-9


def test_is_value_true_at_threshold():
    """is_value is True when best_edge >= 0.05."""
    model_probs = {"home_prob": 0.45, "draw_prob": 0.30, "away_prob": 0.25}
    implied_probs = {"home": 0.39, "draw": 0.32, "away": 0.29}
    v = value_detector.compute_edges(model_probs, implied_probs)
    assert v.best_edge >= 0.05
    assert v.is_value is True

    implied_high = {"home": 0.45, "draw": 0.30, "away": 0.25}
    v_no = value_detector.compute_edges(model_probs, implied_high)
    assert v_no.best_edge < 0.05
    assert v_no.is_value is False


def test_reason_codes_added_correctly():
    """to_reason_codes returns V1 when is_value, V2 when best_edge >= 0.10."""
    v_value = value_detector.ValueSignal(
        edge_home=0.06, edge_draw=0.0, edge_away=0.0,
        best_outcome="home", best_edge=0.06, is_value=True,
    )
    codes = value_detector.to_reason_codes(v_value)
    assert "V1_VALUE_EDGE_PRESENT" in codes
    assert "V2_STRONG_VALUE_EDGE" not in codes

    v_strong = value_detector.ValueSignal(
        edge_home=0.12, edge_draw=0.0, edge_away=0.0,
        best_outcome="home", best_edge=0.12, is_value=True,
    )
    codes_strong = value_detector.to_reason_codes(v_strong)
    assert "V1_VALUE_EDGE_PRESENT" in codes_strong
    assert "V2_STRONG_VALUE_EDGE" in codes_strong

    v_none = value_detector.ValueSignal(
        edge_home=0.02, edge_draw=0.0, edge_away=0.0,
        best_outcome="home", best_edge=0.02, is_value=False,
    )
    codes_none = value_detector.to_reason_codes(v_none)
    assert codes_none == []
