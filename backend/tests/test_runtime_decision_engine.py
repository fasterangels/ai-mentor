"""
Unit tests for live runtime integration of the GO/NO-GO decision engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.runtime.decision_runtime import (  # type: ignore[import-error]
    apply_runtime_decision,
    run_decision_engine_runtime,
)


def _reliability_table() -> dict:
    # Simple reliability table for a single "default" market.
    return {
        "default": {
            "R_HIGH": 0.9,
            "R_MED": 0.7,
            "R_LOW": 0.2,
        }
    }


def test_high_confidence_and_reliable_reasons_go() -> None:
    prediction = {
        "market": "default",
        "confidence": 0.9,
        "reason_codes": ["R_HIGH", "R_MED"],
        "reason_conflicts": False,
    }

    result = run_decision_engine_runtime(prediction, _reliability_table())
    assert result["decision"] == "GO"
    assert "low_confidence" not in result["flags"]


def test_low_confidence_results_in_no_go() -> None:
    prediction = {
        "market": "default",
        "confidence": 0.2,
        "reason_codes": ["R_HIGH", "R_MED"],
        "reason_conflicts": False,
    }

    result = run_decision_engine_runtime(prediction, _reliability_table())
    assert result["decision"] == "NO_GO"
    assert "low_confidence" in result["flags"]


def test_low_reliability_reason_results_in_no_go_and_refusal_annotation() -> None:
    prediction = {
        "market": "default",
        "confidence": 0.9,
        "reason_codes": ["R_HIGH", "R_LOW"],
        "reason_conflicts": False,
    }

    # Direct engine output
    result = run_decision_engine_runtime(prediction, _reliability_table())
    assert result["decision"] == "NO_GO"
    assert "low_reliability_reason_active" in result["flags"]

    # Integration helper should annotate prediction
    updated = apply_runtime_decision(prediction, _reliability_table())
    assert updated.get("refused") is True
    assert "low_reliability_reason_active" in updated.get("refusal_reason", [])

