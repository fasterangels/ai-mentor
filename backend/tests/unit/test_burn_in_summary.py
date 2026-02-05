"""
Unit tests for burn-in summary extractor formatting.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Import from tools (repo root)
_tools = _backend.parent / "tools"
if str(_tools) not in sys.path:
    sys.path.insert(0, str(_tools))

import pytest

from burn_in_summary import format_burn_in_summary


def test_format_burn_in_summary_contains_run_status_alerts_activated() -> None:
    """Summary output contains Run, Status, Alerts, Activated, Matches, Connector."""
    bundle = {
        "run_id": "burn_in_ops_20250101_120000_abc",
        "summary": {
            "run_id": "burn_in_ops_20250101_120000_abc",
            "status": "ok",
            "alerts_count": 0,
            "activated": False,
            "matches_count": 5,
            "connector_name": "stub_live_platform",
        },
    }
    out = format_burn_in_summary(bundle)
    assert "Run:" in out
    assert "burn_in_ops_20250101_120000_abc" in out
    assert "Status:" in out
    assert "ok" in out
    assert "Alerts:" in out
    assert "0" in out
    assert "Activated:" in out
    assert "Matches:" in out
    assert "5" in out
    assert "Connector:" in out
    assert "stub_live_platform" in out


def test_format_burn_in_summary_alert_details_when_present() -> None:
    """When live_analyze has alerts, Alert details section appears."""
    bundle = {
        "summary": {"run_id": "r1", "status": "ok", "alerts_count": 1, "activated": False, "matches_count": 1, "connector_name": "c1"},
        "live_analyze": {
            "alerts": [{"code": "IDENTITY_MISMATCH", "message": "Team names differ"}],
        },
    }
    out = format_burn_in_summary(bundle)
    assert "Alert details:" in out
    assert "IDENTITY_MISMATCH" in out
    assert "Team names differ" in out


def test_format_burn_in_summary_latency_when_present() -> None:
    """When latency_ms present in live_compare or live_analyze, Avg latency line appears."""
    bundle = {
        "summary": {"run_id": "r1", "status": "ok", "alerts_count": 0, "activated": False, "matches_count": 1, "connector_name": "c1"},
        "live_compare": {"latency_ms": 120},
    }
    out = format_burn_in_summary(bundle)
    assert "latency" in out.lower()
    assert "120" in out


def test_format_burn_in_summary_confidence_when_present() -> None:
    """When live_analysis_reports have confidence, Confidence line appears."""
    bundle = {
        "summary": {"run_id": "r1", "status": "ok", "alerts_count": 0, "activated": False, "matches_count": 1, "connector_name": "c1"},
        "live_analyze": {
            "live_analysis_reports": {
                "m1": {"analyzer": {"decisions": [{"market": "1X2", "confidence": 0.65}, {"market": "OU25", "confidence": 0.70}]}},
            },
        },
    }
    out = format_burn_in_summary(bundle)
    assert "Confidence:" in out
    assert "avg=" in out
    assert "count=2" in out or "count=2" in out
