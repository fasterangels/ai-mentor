"""
Unit tests for reason failure envelope metrics.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from evaluation.reason_failure_metrics import (  # type: ignore[attr-defined]
    REASON_FAILURE_METRICS_VERSION,
    compute_reason_failure_metrics,
    reason_failure_metrics_for_report,
)


def test_correct_decision_counts_activation_but_no_failure() -> None:
    """SUCCESS outcome with active reason -> activation only, no failure."""
    decisions = [
        ("one_x_two", "SUCCESS", ["R1"]),
    ]
    out = compute_reason_failure_metrics(decisions)
    r1 = out["R1"]
    assert r1["global"]["activations"] == 1
    assert r1["global"]["failures"] == 0
    assert r1["global"]["failure_rate"] == 0.0
    assert r1["per_market"]["one_x_two"]["activations"] == 1
    assert r1["per_market"]["one_x_two"]["failures"] == 0


def test_incorrect_decision_counts_failure_exposure() -> None:
    """FAILURE outcome with active reason -> activation and failure."""
    decisions = [
        ("one_x_two", "FAILURE", ["R1"]),
        ("one_x_two", "FAILURE", ["R1"]),
        ("one_x_two", "SUCCESS", ["R1"]),
    ]
    out = compute_reason_failure_metrics(decisions)
    r1 = out["R1"]
    assert r1["global"]["activations"] == 3
    assert r1["global"]["failures"] == 2
    assert r1["global"]["failure_rate"] == pytest.approx(2 / 3, rel=1e-3)


def test_multiple_markets_aggregated_correctly() -> None:
    """Per-market activations and failures summed correctly."""
    decisions = [
        ("one_x_two", "FAILURE", ["R1"]),
        ("one_x_two", "SUCCESS", ["R1"]),
        ("over_under_25", "FAILURE", ["R1"]),
        ("over_under_25", "FAILURE", ["R1"]),
    ]
    out = compute_reason_failure_metrics(decisions)
    r1 = out["R1"]
    assert r1["global"]["activations"] == 4
    assert r1["global"]["failures"] == 3
    assert r1["per_market"]["one_x_two"]["activations"] == 2
    assert r1["per_market"]["one_x_two"]["failures"] == 1
    assert r1["per_market"]["over_under_25"]["activations"] == 2
    assert r1["per_market"]["over_under_25"]["failures"] == 2


def test_empty_decisions_returns_empty_metrics() -> None:
    """Empty decisions -> empty reason_failure_metrics."""
    out = compute_reason_failure_metrics([])
    assert out == {}


def test_reason_failure_metrics_for_report_includes_version() -> None:
    """reason_failure_metrics_for_report returns metrics + meta.version."""
    decisions = [("one_x_two", "FAILURE", ["R1"])]
    block = reason_failure_metrics_for_report(decisions)
    assert "reason_failure_metrics" in block
    assert block["reason_failure_metrics"]["R1"]["global"]["activations"] == 1
    assert block["meta"]["reason_failure_metrics_version"] == REASON_FAILURE_METRICS_VERSION

