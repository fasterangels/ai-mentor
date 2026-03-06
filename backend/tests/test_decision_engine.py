"""
Tests for football decision engine: GO, NO_GO, LOW_CONFIDENCE.
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

from backend.football import decision_engine


def test_go_when_value_and_confidence_high():
    """GO when is_value and confidence >= 0.5."""
    payload = {
        "meta": {
            "model_prediction": {"home_prob": 0.55, "draw_prob": 0.25, "away_prob": 0.20},
            "value_signal": {"is_value": True},
            "schedule_fatigue": {"home": {"fatigue_score": 0.2}, "away": {"fatigue_score": 0.2}},
            "injury_impact": {"home": {"injury_impact_score": 0.1}, "away": {"injury_impact_score": 0.1}},
        }
    }
    result = decision_engine.build_decision(payload)
    assert result.decision == "GO"
    assert result.confidence == 0.55
    assert "value_edge" in result.reasons


def test_no_go_when_confidence_low():
    """NO_GO when confidence < 0.45."""
    payload = {
        "meta": {
            "model_prediction": {"home_prob": 0.35, "draw_prob": 0.35, "away_prob": 0.30},
            "value_signal": {"is_value": True},
            "schedule_fatigue": {"home": {"fatigue_score": 0.0}, "away": {"fatigue_score": 0.0}},
            "injury_impact": {"home": {"injury_impact_score": 0.0}, "away": {"injury_impact_score": 0.0}},
        }
    }
    result = decision_engine.build_decision(payload)
    assert result.decision == "NO_GO"
    assert result.confidence == 0.35


def test_low_confidence_when_no_value():
    """LOW_CONFIDENCE when no value edge (confidence >= 0.45 but is_value False or confidence < 0.5)."""
    payload = {
        "meta": {
            "model_prediction": {"home_prob": 0.48, "draw_prob": 0.30, "away_prob": 0.22},
            "value_signal": {"is_value": False},
            "schedule_fatigue": {"home": {"fatigue_score": 0.0}, "away": {"fatigue_score": 0.0}},
            "injury_impact": {"home": {"injury_impact_score": 0.0}, "away": {"injury_impact_score": 0.0}},
        }
    }
    result = decision_engine.build_decision(payload)
    assert result.decision == "LOW_CONFIDENCE"
    assert result.confidence == 0.48
    assert "value_edge" not in result.reasons
