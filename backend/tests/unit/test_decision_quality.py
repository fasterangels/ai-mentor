"""
Unit tests for decision quality: deterministic output given fixed sample history.
Uses small synthetic fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from offline_eval.decision_quality import (
    build_suggestions,
    confidence_calibration,
    compute_decision_quality_report,
    reason_churn_metrics,
    reason_effectiveness_over_time,
    stability_metrics,
)


def _record(run_id: int, created: str, match_id: str, outcomes: dict, reason_codes: dict, predictions: list) -> dict:
    return {
        "run_id": run_id,
        "created_at_utc": created,
        "match_id": match_id,
        "market_outcomes": outcomes,
        "reason_codes_by_market": reason_codes,
        "predictions": predictions,
    }


def test_compute_decision_quality_report_deterministic() -> None:
    """Same input produces identical output."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {"one_x_two": "SUCCESS"}, {"one_x_two": ["R1"]}, [{"market": "1X2", "pick": "home", "confidence": 0.6, "reasons": ["R1"]}]),
        _record(2, "2025-01-02T12:00:00+00:00", "m1", {"one_x_two": "FAILURE"}, {"one_x_two": ["R1"]}, [{"market": "1X2", "pick": "away", "confidence": 0.62, "reasons": ["R1"]}]),
    ]
    r1 = compute_decision_quality_report(records)
    r2 = compute_decision_quality_report(records)
    assert r1["summary"] == r2["summary"]
    assert r1["reason_effectiveness_over_time"] == r2["reason_effectiveness_over_time"]
    assert r1["reason_churn"] == r2["reason_churn"]
    assert r1["stability"] == r2["stability"]


def test_reason_effectiveness_over_time_decay() -> None:
    """Reason effectiveness includes decay-weighted contribution."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {"one_x_two": "SUCCESS"}, {"one_x_two": ["R1"]}, []),
        _record(2, "2025-01-02T12:00:00+00:00", "m1", {"one_x_two": "FAILURE"}, {"one_x_two": ["R1"]}, []),
    ]
    out = reason_effectiveness_over_time(records, half_life_runs=50.0)
    assert "R1" in out
    assert out["R1"]["win_count"] == 1
    assert out["R1"]["loss_count"] == 1
    assert "decayed_contribution" in out["R1"]


def test_reason_churn_metrics() -> None:
    """Churn counts appearances and disappearances across runs."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {}, {"one_x_two": ["R1"]}, []),
        _record(2, "2025-01-02T12:00:00+00:00", "m1", {}, {"one_x_two": ["R1", "R2"]}, []),
        _record(3, "2025-01-03T12:00:00+00:00", "m1", {}, {"one_x_two": ["R2"]}, []),
    ]
    out = reason_churn_metrics(records)
    assert out["total_transitions"] == 2
    assert out["appearance_count"] >= 1
    assert out["disappearance_count"] >= 1


def test_confidence_calibration_bins() -> None:
    """Calibration has predicted_confidence and empirical_accuracy per band."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {"one_x_two": "SUCCESS"}, {}, [{"market": "1X2", "pick": "home", "confidence": 0.52, "reasons": []}]),
        _record(2, "2025-01-02T12:00:00+00:00", "m1", {"one_x_two": "FAILURE"}, {}, [{"market": "1X2", "pick": "home", "confidence": 0.52, "reasons": []}]),
    ]
    out = confidence_calibration(records)
    assert "one_x_two" in out
    for band, data in out["one_x_two"].items():
        assert "predicted_confidence" in data
        assert "empirical_accuracy" in data or data.get("count") == 0


def test_stability_pick_flip_and_volatility() -> None:
    """Stability includes pick_flip_rate and confidence_volatility_p95."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {"one_x_two": "SUCCESS"}, {}, [{"market": "1X2", "pick": "home", "confidence": 0.6, "reasons": []}]),
        _record(2, "2025-01-02T12:00:00+00:00", "m1", {"one_x_two": "SUCCESS"}, {}, [{"market": "1X2", "pick": "away", "confidence": 0.7, "reasons": []}]),
    ]
    out = stability_metrics(records)
    assert "pick_flip_rate" in out
    assert "confidence_volatility_p95" in out
    assert out["pick_flip_denom"] == 1
    assert out["pick_flip_count"] == 1


def test_suggestions_dampening_and_band_adjustments() -> None:
    """Suggestions contain dampening_candidates and confidence_band_adjustments (suggestions only)."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {"one_x_two": "FAILURE"}, {"one_x_two": ["R_weak"]}, [{"market": "1X2", "pick": "home", "confidence": 0.55, "reasons": []}]),
    ] * 10
    reason_eff = reason_effectiveness_over_time(records)
    calibration = confidence_calibration(records)
    suggestions = build_suggestions(records, reason_eff, calibration, effectiveness_decay_threshold=0.05, calibration_deviation_threshold=0.1)
    assert "dampening_candidates" in suggestions
    assert "confidence_band_adjustments" in suggestions
    for c in suggestions.get("dampening_candidates", []):
        assert "suggestion" in c
        assert "reason_code" in c
