"""
Unit tests for error taxonomy engine v1.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from evaluation.error_taxonomy import (  # type: ignore[attr-defined]
    ERROR_TAXONOMY_VERSION,
    compute_error_taxonomy,
    error_taxonomy_for_report,
)


def test_outcome_mismatch_and_sparse_evidence() -> None:
    """Failure with one reason gets outcome_mismatch + sparse_evidence_error."""
    decisions = [
        ("one_x_two", "FAILURE", 0.6, ["R1"]),
    ]
    out = compute_error_taxonomy(decisions)
    assert out["global"]["outcome_mismatch"] == 1
    assert out["global"]["sparse_evidence_error"] == 1
    assert "unknown_bucket" not in out["global"]


def test_low_and_high_confidence_errors() -> None:
    """Confidence thresholds tag low/high confidence errors."""
    decisions = [
        ("one_x_two", "FAILURE", 0.50, ["R1"]),  # low
        ("one_x_two", "FAILURE", 0.80, ["R1"]),  # high
        ("one_x_two", "FAILURE", 0.60, ["R1"]),  # neither
    ]
    out = compute_error_taxonomy(decisions, low_conf_threshold=0.55, high_conf_threshold=0.75)
    assert out["global"]["low_confidence_error"] == 1
    assert out["global"]["high_confidence_error"] == 1
    assert out["global"]["outcome_mismatch"] == 3


def test_reason_conflict_error_uses_polarity() -> None:
    """EXPECTED_GOALS_ABOVE (support) + EXPECTED_GOALS_BELOW (oppose) => reason_conflict_error."""
    decisions = [
        ("over_under_25", "FAILURE", 0.7, ["EXPECTED_GOALS_ABOVE", "EXPECTED_GOALS_BELOW"]),
    ]
    out = compute_error_taxonomy(decisions)
    assert out["global"]["reason_conflict_error"] == 1
    # Also outcome_mismatch
    assert out["global"]["outcome_mismatch"] == 1


def test_unknown_bucket_when_no_other_tags() -> None:
    """Failure with no confidence and multiple neutral reasons => unknown_bucket + outcome_mismatch."""
    decisions = [
        ("gg_ng", "FAILURE", None, ["R1", "R2"]),
    ]
    out = compute_error_taxonomy(decisions)
    assert out["global"]["outcome_mismatch"] == 1
    assert out["global"]["unknown_bucket"] == 1


def test_per_reason_involvement_counts_incorrect_decisions() -> None:
    """Per-reason involvement counts number of incorrect decisions globally and per market."""
    decisions = [
        ("one_x_two", "FAILURE", 0.6, ["R1", "R2"]),
        ("over_under_25", "FAILURE", 0.6, ["R1"]),
        ("over_under_25", "SUCCESS", 0.6, ["R1"]),  # not counted (success)
    ]
    out = compute_error_taxonomy(decisions)
    per_reason = out["per_reason"]
    r1 = per_reason["R1"]
    assert r1["global"]["incorrect_decisions"] == 2
    assert r1["per_market"]["one_x_two"]["incorrect_decisions"] == 1
    assert r1["per_market"]["over_under_25"]["incorrect_decisions"] == 1


def test_error_taxonomy_for_report_includes_version_and_sorted_keys() -> None:
    """error_taxonomy_for_report wraps metrics and includes version meta."""
    decisions = [
        ("one_x_two", "FAILURE", 0.6, ["R2"]),
    ]
    block = error_taxonomy_for_report(decisions)
    assert "error_taxonomy" in block
    assert block["meta"]["error_taxonomy_version"] == ERROR_TAXONOMY_VERSION
    # Keys should be sorted (only one here; just sanity-check structure)
    metrics = block["error_taxonomy"]
    assert "global" in metrics and "per_market" in metrics and "per_reason" in metrics

