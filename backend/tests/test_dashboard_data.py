"""
Unit tests for the Decision Intelligence dashboard data layer.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.dashboard.dashboard_data import (  # type: ignore[import-error]
    DashboardConfig,
    build_dashboard_data,
)


def test_basic_aggregation() -> None:
    report = {
        "decision_engine_metrics": {
            "summary": {
                "n": 100,
                "go": 60,
                "no_go": 40,
                "go_rate": 0.6,
            },
            "avg_conf_raw": 0.7,
            "avg_conf_cal": 0.65,
            "per_market": {
                "A": {"n": 70, "go": 42, "no_go": 28, "go_rate": 0.6},
                "B": {"n": 30, "go": 18, "no_go": 12, "go_rate": 0.6},
            },
        },
        "reason_reliability": {
            "global": {
                "R1": 0.4,
                "R2": 0.2,
                "R3": 0.9,
            }
        },
        "system_audit": {
            "red_flags": [
                {"type": "low_precision_market", "market": "A", "value": 0.4},
            ]
        },
        "meta": {
            "decision_engine_version": "dev0",
            "decision_policy_version": "v1",
            "calibrator_version": "v0",
            "refusal_tradeoff_version": "v0",
            "system_audit_version": "v0",
        },
    }

    cfg = DashboardConfig(top_k_markets=2, version="v_test")
    dashboard = build_dashboard_data(report, cfg)

    assert dashboard["version"] == "v_test"
    g = dashboard["global"]
    assert g["n_predictions"] == 100
    assert g["go_rate"] == 0.6
    assert g["no_go_rate"] == 0.4

    markets = dashboard["markets"]
    assert len(markets) == 2
    # Sorted by n descending: A first
    assert markets[0]["market"] == "A"
    assert markets[0]["n"] == 70

    reasons = dashboard["reasons"]
    # Sorted by reliability ascending: R2 (0.2) first
    assert reasons[0]["reason"] == "R2"
    assert reasons[0]["reliability"] == 0.2

    audit = dashboard["audit"]
    assert audit["red_flags"] == 1

    meta = dashboard["meta"]
    # Keys should include only the selected meta fields
    expected_meta_keys = {
        "calibrator_version",
        "decision_engine_version",
        "decision_policy_version",
        "refusal_tradeoff_version",
        "system_audit_version",
    }
    assert set(meta.keys()) == expected_meta_keys


def test_missing_sections_defaults() -> None:
    # Report missing reason_reliability and system_audit should not crash.
    report = {
        "decision_engine_metrics": {
            "summary": {
                "n": 10,
                "go": 5,
                "no_go": 5,
            },
        },
    }
    cfg = DashboardConfig()
    dashboard = build_dashboard_data(report, cfg)

    g = dashboard["global"]
    assert g["n_predictions"] == 10
    # go_rate should be derived from counts
    assert g["go_rate"] == 0.5
    assert g["no_go_rate"] == 0.5

    # No reasons and no audit flags by default
    assert dashboard["reasons"] == []
    assert dashboard["audit"]["red_flags"] == 0

