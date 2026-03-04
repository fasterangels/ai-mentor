"""
Unit tests for the system self-audit report generator.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.audit.system_audit import (  # type: ignore[import-error]
    AuditConfig,
    generate_audit,
)


def _make_basic_report() -> dict:
    return {
        "decision_engine_metrics": {
            "summary": {
                "n": 4,
                "go": 2,
                "no_go": 2,
                "go_rate": 0.5,
            },
            "avg_conf_raw": 0.7,
            "avg_conf_cal": 0.65,
        },
        "decision_engine_outputs": [
            {"id": "p1", "market": "A", "decision": "GO", "conf_raw": 0.8, "conf_cal": 0.7, "outcome": 1},
            {"id": "p2", "market": "A", "decision": "NO_GO", "conf_raw": 0.6, "conf_cal": 0.6, "outcome": 0},
            {"id": "p3", "market": "B", "decision": "GO", "conf_raw": 0.9, "conf_cal": 0.8, "outcome": 1},
            {"id": "p4", "market": "B", "decision": "NO_GO", "conf_raw": 0.4, "conf_cal": 0.4, "outcome": 0},
        ],
    }


def test_basic_audit_generation_global_and_per_market_metrics() -> None:
    report = _make_basic_report()
    cfg = AuditConfig(min_samples=1)  # allow flags even with few samples for testing

    audit = generate_audit(report, cfg)

    assert audit["version"] == cfg.version
    gm = audit["global_metrics"]
    assert "n_predictions" in gm and gm["n_predictions"] == 4
    assert "go_rate" in gm and "no_go_rate" in gm
    assert "avg_conf_raw" in gm and "avg_conf_cal" in gm
    assert "calibration_drift" in gm
    assert "precision" in gm

    pm = audit["per_market_metrics"]
    # Deterministic ordering of markets
    assert list(pm.keys()) == sorted(pm.keys())
    assert set(pm.keys()) == {"A", "B"}
    for metrics in pm.values():
        for key in ("n_predictions", "go_rate", "no_go_rate", "avg_conf_raw", "avg_conf_cal", "calibration_drift", "precision"):
            assert key in metrics


def test_low_precision_red_flag() -> None:
    # Many incorrect GO decisions to force low precision.
    report = {
        "decision_engine_metrics": {
            "summary": {"n": 5, "go": 5, "no_go": 0},
            "avg_conf_raw": 0.8,
            "avg_conf_cal": 0.8,
        },
        "decision_engine_outputs": [
            {"id": i, "market": "A", "decision": "GO", "conf_raw": 0.8, "conf_cal": 0.8, "outcome": (1 if i == 0 else 0)}
            for i in range(5)
        ],
    }
    cfg = AuditConfig(min_samples=1, low_precision_threshold=0.8)

    audit = generate_audit(report, cfg)
    types = {(f["type"], f["market"]) for f in audit["red_flags"]}
    assert ("low_precision_market", "A") in types or ("low_precision_market", "global") in types


def test_calibration_drift_red_flag() -> None:
    report = {
        "decision_engine_metrics": {
            "summary": {"n": 60, "go": 30, "no_go": 30},
            "avg_conf_raw": 0.9,
            "avg_conf_cal": 0.6,
        },
        "decision_engine_outputs": [
            {"id": i, "market": "A", "decision": "GO", "conf_raw": 0.9, "conf_cal": 0.6, "outcome": 1}
            for i in range(60)
        ],
    }
    cfg = AuditConfig(min_samples=10, calibration_drift_threshold=0.1)

    audit = generate_audit(report, cfg)
    drift_flags = [f for f in audit["red_flags"] if f["type"] == "calibration_drift"]
    assert drift_flags  # at least one drift flag present

