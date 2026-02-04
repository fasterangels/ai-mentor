"""
Integration test: run quality-audit over a small pre-seeded history; assert report schema and key fields.
Uses synthetic history (no external DB) for determinism and speed.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from offline_eval.decision_quality import compute_decision_quality_report


def _record(run_id: int, created: str, match_id: str, outcomes: dict, reason_codes: dict, predictions: list) -> dict:
    return {
        "run_id": run_id,
        "created_at_utc": created,
        "match_id": match_id,
        "market_outcomes": outcomes,
        "reason_codes_by_market": reason_codes,
        "predictions": predictions,
    }


def test_quality_audit_report_schema_and_fields() -> None:
    """Run quality audit over small pre-seeded (synthetic) history; assert report schema and key fields."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {"one_x_two": "SUCCESS"}, {"one_x_two": ["R1"]}, [{"market": "1X2", "pick": "home", "confidence": 0.6, "reasons": ["R1"]}]),
        _record(2, "2025-01-02T12:00:00+00:00", "m1", {"one_x_two": "FAILURE"}, {"one_x_two": ["R1"]}, [{"market": "1X2", "pick": "away", "confidence": 0.62, "reasons": ["R1"]}]),
    ]
    report = compute_decision_quality_report(records)

    assert "summary" in report
    assert "run_count" in report["summary"]
    assert report["summary"]["run_count"] == 2

    assert "reason_effectiveness_over_time" in report
    assert "reason_churn" in report
    assert "confidence_calibration" in report
    assert "stability" in report
    assert "suggestions" in report

    assert "total_transitions" in report["reason_churn"]
    assert "pick_flip_rate" in report["stability"]
    assert "confidence_volatility_p95" in report["stability"]

    assert "dampening_candidates" in report["suggestions"]
    assert "confidence_band_adjustments" in report["suggestions"]

    for market in ("one_x_two", "over_under_25", "gg_ng"):
        assert market in report["confidence_calibration"]
