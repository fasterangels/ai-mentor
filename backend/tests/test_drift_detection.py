"""
Unit tests for reason and score drift detection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.audit.drift_detection import (  # type: ignore[import-error]
    DriftConfig,
    compute_reason_drift,
    compute_score_drift,
    detect_drift,
)


def test_score_drift_detection_triggers_alert() -> None:
    prev_report = {
        "decision_engine_outputs": [
            {"score": 0.3} for _ in range(100)
        ],
    }
    curr_report = {
        "decision_engine_outputs": [
            {"score": 0.6} for _ in range(100)
        ],
    }
    cfg = DriftConfig(score_drift_threshold=0.15, min_samples=50)

    out = detect_drift(prev_report, curr_report, cfg)
    assert out["score_drift"] == 0.3
    types = {a["type"] for a in out["alerts"]}
    assert "score_drift" in types


def test_reason_drift_detection_triggers_alert() -> None:
    prev_report = {
        "decision_engine_outputs": [
            {"score": 0.5, "flags": ["R1"]} for _ in range(100)
        ],
    }
    curr_report = {
        "decision_engine_outputs": [
            {"score": 0.5, "flags": ["R1"]} for _ in range(10)
        ]
        + [
            {"score": 0.5, "flags": ["R2"]} for _ in range(90)
        ],
    }
    cfg = DriftConfig(reason_drift_threshold=0.20, min_samples=10)

    out = detect_drift(prev_report, curr_report, cfg)
    # R1 should show substantial drift (activations dropped from 100 to 10).
    r_drift = out["reason_drift"]
    assert r_drift["R1"] > cfg.reason_drift_threshold

    alerts = [a for a in out["alerts"] if a["type"] == "reason_drift" and a["reason"] == "R1"]
    assert alerts

