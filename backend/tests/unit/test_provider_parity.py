"""
Unit tests for provider parity: compare determinism, ordering, identity/market/odds/schema.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.parity.provider_parity import (
    DEFAULT_POLICY,
    compare,
)


def _snap(match_id: str, home: str = "Home", away: str = "Away", kickoff: str = "2025-10-01T18:00:00+00:00", odds: dict | None = None) -> dict:
    return {
        "match_id": match_id,
        "data": {
            "match_id": match_id,
            "home_team": home,
            "away_team": away,
            "competition": "L",
            "kickoff_utc": kickoff,
            "odds_1x2": odds or {"home": 2.0, "draw": 3.0, "away": 3.5},
            "status": "scheduled",
        },
    }


def test_compare_determinism_same_input_same_output() -> None:
    """Same input produces identical output (deterministic)."""
    a_list = [_snap("m1"), _snap("m2")]
    b_list = [_snap("m1"), _snap("m2")]
    r1 = compare(a_list, b_list)
    r2 = compare(a_list, b_list)
    assert r1["summary"] == r2["summary"]
    assert r1["identity_mismatches"] == r2["identity_mismatches"]
    assert r1["alerts"] == r2["alerts"]


def test_compare_ordering_match_ids_sorted() -> None:
    """Report keys and iteration use sorted match_id order."""
    a_list = [_snap("m2"), _snap("m1")]
    b_list = [_snap("m2"), _snap("m1")]
    r = compare(a_list, b_list)
    match_ids_in_report = list(r["identity_mismatches"].keys()) + [k for k in r["odds_drift"]["per_match"] if k not in r["identity_mismatches"]]
    assert sorted(match_ids_in_report) == ["m1", "m2"]


def test_compare_identity_mismatch() -> None:
    """Identity mismatch (teams/kickoff) is reported."""
    a_list = [_snap("m1", home="TeamA", away="TeamB")]
    b_list = [_snap("m1", home="TeamX", away="TeamY")]
    r = compare(a_list, b_list)
    assert r["summary"]["identity_mismatch_count"] == 1
    assert "m1" in r["identity_mismatches"]
    assert r["identity_mismatches"]["m1"]["provider_a"]["home_team"] == "TeamA"
    assert r["identity_mismatches"]["m1"]["provider_b"]["home_team"] == "TeamX"


def test_compare_market_availability_mismatch() -> None:
    """Market availability (missing keys) is reported."""
    a_list = [_snap("m1", odds={"home": 2.0, "draw": 3.0, "away": 3.5})]
    b_data = _snap("m1", odds={"home": 2.1})
    b_data["data"]["odds_1x2"] = {"home": 2.1}
    b_list = [b_data]
    r = compare(a_list, b_list)
    assert "m1" in r["market_availability_mismatches"]
    assert "missing_in_b" in r["market_availability_mismatches"]["m1"]


def test_compare_odds_drift_outliers_and_distribution() -> None:
    """Odds drift outliers and distribution are in report."""
    a_list = [_snap("m1", odds={"home": 2.0, "draw": 3.0, "away": 3.5})]
    b_list = [_snap("m1", odds={"home": 2.5, "draw": 3.0, "away": 3.5})]
    r = compare(a_list, b_list)
    assert r["odds_drift"]["per_match"]["m1"]["deltas"]["home"]["abs_delta"] == 0.5
    assert r["odds_drift"]["outlier_count"] >= 1
    assert "distribution" in r["odds_drift"]
    assert "pct_delta" in r["odds_drift"]["distribution"]


def test_compare_schema_drift_counts() -> None:
    """Schema drift (missing/type) is counted."""
    a_list = [_snap("m1")]
    b_list = [{"match_id": "m1", "data": {"match_id": "m1"}}]  # missing many fields
    r = compare(a_list, b_list)
    assert r["summary"]["schema_drift_count"] >= 1
    assert "m1" in r["schema_drift"]


def test_compare_guardrails_emit_alerts_only() -> None:
    """Guardrails emit alerts when thresholds exceeded; no exception."""
    a_list = [_snap("m1", home="A", away="B"), _snap("m2", home="A", away="B")]
    b_list = [_snap("m1", home="X", away="Y"), _snap("m2", home="X", away="Y")]
    policy = {"max_identity_mismatch_count": 0}
    r = compare(a_list, b_list, policy=policy)
    assert "alerts" in r
    assert any("PARITY_IDENTITY_MISMATCH" in (a.get("code") or "") for a in r["alerts"])
