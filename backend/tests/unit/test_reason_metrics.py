"""
Unit tests for reason co-activation and conflict metrics (synthetic decisions).
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from evaluation.reason_metrics import (
    compute_reason_metrics,
    reason_metrics_for_report,
)


def test_coactivation_counts_diagonal_and_pairs() -> None:
    """Co-activation: diagonal = total activations; (i,j) = times active together."""
    decisions = [
        ("one_x_two", ["R1", "R2"]),
        ("one_x_two", ["R1", "R2"]),
        ("one_x_two", ["R1"]),
        ("gg_ng", ["R2", "R3"]),
    ]
    out = compute_reason_metrics(decisions)
    co = out["coactivation"]
    global_mat = co["global"]
    # R1 with R1: 3 (three decisions with R1)
    assert global_mat.get("R1", {}).get("R1") == 3
    # R1 with R2: 2 (two decisions have both)
    assert global_mat.get("R1", {}).get("R2") == 2
    assert global_mat.get("R2", {}).get("R1") == 2
    # R2 with R2: 3
    assert global_mat.get("R2", {}).get("R2") == 3
    # R3 with R3: 1
    assert global_mat.get("R3", {}).get("R3") == 1
    # R2 with R3: 1
    assert global_mat.get("R2", {}).get("R3") == 1
    per_market = co["per_market"]
    assert per_market["one_x_two"]["R1"]["R2"] == 2
    assert per_market["gg_ng"]["R2"]["R3"] == 1


def test_conflict_count_and_rate_with_polarity() -> None:
    """Conflict = opposite polarity (support vs oppose) in same decision."""
    # Use codes that have polarity in REASON_POLARITY
    decisions = [
        ("one_x_two", ["EXPECTED_GOALS_ABOVE", "EXPECTED_GOALS_BELOW"]),  # 1 conflict
        ("one_x_two", ["EXPECTED_GOALS_ABOVE", "EXPECTED_GOALS_BELOW"]),  # 1 conflict
        ("one_x_two", ["EXPECTED_GOALS_ABOVE"]),  # no conflict
    ]
    out = compute_reason_metrics(decisions)
    conf = out["conflicts"]
    assert conf["global"]["conflict_count"] == 2
    assert conf["global"]["decision_count"] == 3
    assert conf["global"]["conflict_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert len(conf["global"]["top_pairs"]) >= 1
    assert conf["global"]["top_pairs"][0]["reason_a"] == "EXPECTED_GOALS_ABOVE"
    assert conf["global"]["top_pairs"][0]["reason_b"] == "EXPECTED_GOALS_BELOW"
    assert conf["global"]["top_pairs"][0]["count"] == 2


def test_no_conflict_when_neutral_or_same_polarity() -> None:
    """Neutral codes or same polarity do not count as conflict."""
    decisions = [
        ("one_x_two", ["R1", "R2"]),  # both neutral -> 0 conflict
        ("one_x_two", ["EXPECTED_GOALS_ABOVE", "R1"]),  # support + neutral -> 0
    ]
    out = compute_reason_metrics(decisions)
    assert out["conflicts"]["global"]["conflict_count"] == 0
    assert out["conflicts"]["global"]["conflict_rate"] == 0.0


def test_empty_decisions_returns_empty_metrics() -> None:
    """Empty decisions -> empty coactivation, zero conflicts."""
    out = compute_reason_metrics([])
    assert out["coactivation"]["global"] == {}
    assert out["coactivation"]["per_market"] == {}
    assert out["conflicts"]["global"]["conflict_count"] == 0
    assert out["conflicts"]["global"]["conflict_rate"] == 0.0
    assert out["conflicts"]["global"]["decision_count"] == 0
    assert out["conflicts"]["global"]["top_pairs"] == []


def test_reason_metrics_for_report_includes_version() -> None:
    """reason_metrics_for_report returns reason_metrics + meta.reason_metrics_version."""
    decisions = [("one_x_two", ["R1"])]
    block = reason_metrics_for_report(decisions)
    assert "reason_metrics" in block
    assert block["reason_metrics"]["coactivation"]["global"]["R1"]["R1"] == 1
    assert block["meta"]["reason_metrics_version"] == 1

