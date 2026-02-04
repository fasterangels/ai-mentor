"""
Unit tests for live shadow analyze guardrails: pick change rate, confidence delta, coverage drop, reason churn.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from reports.live_shadow_analyze_guardrails import (
    DEFAULT_POLICY,
    _calculate_confidence_deltas,
    _calculate_coverage_drop,
    _calculate_pick_change_rate,
    _calculate_reason_churn_rate,
    _extract_decisions,
    compare_analysis,
    evaluate,
)


def test_extract_decisions_from_analysis() -> None:
    """_extract_decisions extracts picks, confidence, reasons from analysis report."""
    analysis = {
        "analysis": {
            "markets_picks_confidences": {
                "1X2": {"pick": "HOME", "confidence": 0.75},
                "OU_2.5": {"pick": "OVER", "confidence": 0.60},
            },
            "decisions": [
                {"market": "1X2", "selection": "HOME", "confidence": 0.75, "reasons": ["reason1", "reason2"]},
                {"market": "OU_2.5", "selection": "OVER", "confidence": 0.60, "reasons": ["reason3"]},
            ],
        }
    }
    decisions = _extract_decisions(analysis)
    assert "1X2" in decisions
    assert decisions["1X2"]["pick"] == "HOME"
    assert decisions["1X2"]["confidence"] == 0.75
    assert decisions["1X2"]["reasons"] == ["reason1", "reason2"]


def test_calculate_pick_change_rate() -> None:
    """Pick change rate calculated correctly."""
    live = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": []}}
    rec = {"1X2": {"pick": "AWAY", "confidence": 0.70, "reasons": []}}
    rate = _calculate_pick_change_rate(live, rec)
    assert rate == 1.0

    live2 = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": []}, "OU_2.5": {"pick": "OVER", "confidence": 0.60, "reasons": []}}
    rec2 = {"1X2": {"pick": "HOME", "confidence": 0.70, "reasons": []}, "OU_2.5": {"pick": "OVER", "confidence": 0.60, "reasons": []}}
    rate2 = _calculate_pick_change_rate(live2, rec2)
    assert rate2 == 0.0


def test_calculate_confidence_deltas() -> None:
    """Confidence deltas calculated correctly."""
    live = {"1X2": {"pick": "HOME", "confidence": 0.80, "reasons": []}}
    rec = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": []}}
    deltas = _calculate_confidence_deltas(live, rec)
    assert len(deltas) == 1
    assert abs(deltas[0] - 0.05) < 0.0001


def test_calculate_coverage_drop() -> None:
    """Coverage drop calculated correctly."""
    live = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": []}}
    rec = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": []}, "OU_2.5": {"pick": "OVER", "confidence": 0.60, "reasons": []}}
    drop = _calculate_coverage_drop(live, rec)
    assert drop == 50.0


def test_calculate_reason_churn_rate() -> None:
    """Reason churn rate calculated correctly."""
    live = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": ["reason1", "reason2"]}}
    rec = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": ["reason1", "reason3"]}}
    churn = _calculate_reason_churn_rate(live, rec)
    assert churn == 1.0

    live2 = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": ["reason1"]}}
    rec2 = {"1X2": {"pick": "HOME", "confidence": 0.75, "reasons": ["reason1"]}}
    churn2 = _calculate_reason_churn_rate(live2, rec2)
    assert churn2 == 0.0


def test_evaluate_alerts_when_threshold_exceeded() -> None:
    """Guardrails emit alerts when thresholds exceeded."""
    policy = {**DEFAULT_POLICY, "max_pick_change_rate": 0.0}
    live_analysis = {
        "analysis": {
            "markets_picks_confidences": {"1X2": {"pick": "HOME", "confidence": 0.75}},
            "decisions": [{"market": "1X2", "selection": "HOME", "confidence": 0.75, "reasons": []}],
        }
    }
    recorded_analysis = {
        "analysis": {
            "markets_picks_confidences": {"1X2": {"pick": "AWAY", "confidence": 0.70}},
            "decisions": [{"market": "1X2", "selection": "AWAY", "confidence": 0.70, "reasons": []}],
        }
    }
    alerts = evaluate(live_analysis, recorded_analysis, policy=policy)
    codes = [a["code"] for a in alerts]
    assert "LIVE_SHADOW_PICK_CHANGE_RATE" in codes


def test_evaluate_no_alerts_under_threshold() -> None:
    """No alerts when all metrics under thresholds."""
    live_analysis = {
        "analysis": {
            "markets_picks_confidences": {"1X2": {"pick": "HOME", "confidence": 0.75}},
            "decisions": [{"market": "1X2", "selection": "HOME", "confidence": 0.75, "reasons": ["r1"]}],
        }
    }
    recorded_analysis = {
        "analysis": {
            "markets_picks_confidences": {"1X2": {"pick": "HOME", "confidence": 0.75}},
            "decisions": [{"market": "1X2", "selection": "HOME", "confidence": 0.75, "reasons": ["r1"]}],
        }
    }
    alerts = evaluate(live_analysis, recorded_analysis)
    assert len(alerts) == 0


def test_compare_analysis_structure() -> None:
    """compare_analysis returns pick_parity, confidence_deltas, reasons_diff, coverage_diff."""
    live_analysis = {
        "analysis": {
            "markets_picks_confidences": {"1X2": {"pick": "HOME", "confidence": 0.80}},
            "decisions": [{"market": "1X2", "selection": "HOME", "confidence": 0.80, "reasons": ["r1", "r2"]}],
        }
    }
    recorded_analysis = {
        "analysis": {
            "markets_picks_confidences": {"1X2": {"pick": "HOME", "confidence": 0.75}, "OU_2.5": {"pick": "OVER", "confidence": 0.60}},
            "decisions": [
                {"market": "1X2", "selection": "HOME", "confidence": 0.75, "reasons": ["r1"]},
                {"market": "OU_2.5", "selection": "OVER", "confidence": 0.60, "reasons": []},
            ],
        }
    }
    result = compare_analysis(live_analysis, recorded_analysis)
    assert "pick_parity" in result
    assert "confidence_deltas" in result
    assert "reasons_diff" in result
    assert "coverage_diff" in result
    assert result["pick_parity"]["1X2"]["parity"] is True
    assert abs(result["confidence_deltas"]["1X2"] - 0.05) < 0.0001
    assert "r2" in result["reasons_diff"]["1X2"]["added"]
    assert "OU_2.5" in result["coverage_diff"]["missing_in_live"]
