"""
Tests for guardrail alerts: deterministic rules from batch_report.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from reports.alerts import evaluate_alerts


def test_no_matches_info_alert() -> None:
    batch_report = {
        "aggregates": {"total_matches": 0, "total_changed_decisions": 0, "per_market_changed_counts": {}},
        "failures": [],
    }
    alerts = evaluate_alerts(batch_report)
    codes = [a["code"] for a in alerts]
    assert "NO_MATCHES" in codes
    no_m = next(a for a in alerts if a["code"] == "NO_MATCHES")
    assert no_m["severity"] == "INFO"
    assert "No matches" in no_m["message"]


def test_changes_spike_warn_alert() -> None:
    # total_changed_decisions > 0.3 * total_matches (e.g. 4 > 0.3*10)
    batch_report = {
        "aggregates": {
            "total_matches": 10,
            "total_changed_decisions": 4,
            "per_market_changed_counts": {},
        },
        "failures": [],
    }
    alerts = evaluate_alerts(batch_report)
    codes = [a["code"] for a in alerts]
    assert "CHANGES_SPIKE" in codes
    spike = next(a for a in alerts if a["code"] == "CHANGES_SPIKE")
    assert spike["severity"] == "WARN"
    assert "30%" in spike["message"]


def test_market_changes_spike_warn_alert() -> None:
    # one market count > 0.4 * total_matches (e.g. 5 > 0.4*10)
    batch_report = {
        "aggregates": {
            "total_matches": 10,
            "total_changed_decisions": 0,
            "per_market_changed_counts": {"1X2": 5, "OU_2.5": 2},
        },
        "failures": [],
    }
    alerts = evaluate_alerts(batch_report)
    codes = [a["code"] for a in alerts]
    assert "MARKET_CHANGES_SPIKE" in codes
    market_alerts = [a for a in alerts if a["code"] == "MARKET_CHANGES_SPIKE"]
    assert len(market_alerts) == 1
    assert market_alerts[0]["severity"] == "WARN"
    assert "1X2" in market_alerts[0]["message"]
    assert "40%" in market_alerts[0]["message"]


def test_partial_failures_warn_alert() -> None:
    batch_report = {
        "aggregates": {"total_matches": 2, "total_changed_decisions": 0, "per_market_changed_counts": {}},
        "failures": [{"match_id": "m1", "error": "NO_EVIDENCE_PACK"}],
    }
    alerts = evaluate_alerts(batch_report)
    codes = [a["code"] for a in alerts]
    assert "PARTIAL_FAILURES" in codes
    pf = next(a for a in alerts if a["code"] == "PARTIAL_FAILURES")
    assert pf["severity"] == "WARN"
    assert "1 failure" in pf["message"]


def test_deterministic_same_input_same_alerts() -> None:
    batch_report = {
        "aggregates": {
            "total_matches": 10,
            "total_changed_decisions": 2,
            "per_market_changed_counts": {"1X2": 1},
        },
        "failures": [],
    }
    a1 = evaluate_alerts(batch_report)
    a2 = evaluate_alerts(batch_report)
    assert [x["code"] for x in a1] == [x["code"] for x in a2]
    assert [x["message"] for x in a1] == [x["message"] for x in a2]


def test_empty_report_no_crash() -> None:
    alerts = evaluate_alerts({})
    assert isinstance(alerts, list)
    # total_matches 0 -> NO_MATCHES
    assert any(a["code"] == "NO_MATCHES" for a in alerts)
