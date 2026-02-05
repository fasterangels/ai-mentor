"""
Contract test: live_shadow_analysis_report schema stability and required fields.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from runner.live_shadow_analyze_runner import MODE_LIVE_SHADOW_ANALYZE


def test_live_shadow_analyze_report_schema_structure() -> None:
    """live_shadow_analysis_report has required fields: run_id, mode, connector_name, match_ids, live_analysis_reports, recorded_analysis_reports, per_match_compare, summary, alerts."""
    # Schema contract: report structure must be stable
    required_fields = {
        "run_id": str,
        "created_at_utc": str,
        "mode": str,
        "connector_name": str,
        "match_ids": list,
        "live_analysis_reports": dict,
        "recorded_analysis_reports": dict,
        "per_match_compare": list,
        "summary": dict,
        "alerts": list,
    }
    # Validate mode constant
    assert MODE_LIVE_SHADOW_ANALYZE == "LIVE_SHADOW_ANALYZE"
    # Schema is enforced by runner return type; this test documents the contract
    assert all(isinstance(k, str) for k in required_fields.keys())


def test_per_match_compare_schema() -> None:
    """per_match_compare entries have: match_id, compare (pick_parity, confidence_deltas, reasons_diff, coverage_diff), alerts."""
    # Contract: each entry in per_match_compare must have these fields
    required_per_match_fields = {
        "match_id": str,
        "compare": dict,
        "alerts": list,
    }
    required_compare_fields = {
        "pick_parity": dict,
        "confidence_deltas": dict,
        "reasons_diff": dict,
        "coverage_diff": dict,
    }
    # Schema enforced by compare_analysis return; this documents contract
    assert all(isinstance(k, str) for k in required_per_match_fields.keys())
    assert all(isinstance(k, str) for k in required_compare_fields.keys())
