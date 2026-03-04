"""
Unit tests for Reason Reliability Index (beta-smoothed reliability per reason).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from evaluation.reason_reliability import (  # type: ignore[attr-defined]
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    compute_reason_reliability,
    reason_reliability_for_report,
)


def test_small_sample_shrinks_toward_prior() -> None:
    """With very few observations, reliability is pulled toward the Beta prior."""
    failure_metrics = {
        "R1": {
            "global": {"activations": 1, "failures": 1},
            "per_market": {"one_x_two": {"activations": 1, "failures": 1}},
        }
    }
    out = compute_reason_reliability(failure_metrics, alpha=2.0, beta=2.0)
    r1 = out["R1"]["global"]
    # Empirical reliability would be 0.0; smoothed should be > 0
    assert r1["activations"] == 1
    assert r1["failures"] == 1
    assert 0.0 < r1["reliability"] < 1.0


def test_large_sample_approximates_empirical() -> None:
    """With many observations, reliability is close to empirical (1 - failure_rate)."""
    failure_metrics = {
        "R1": {
            "global": {"activations": 100, "failures": 20},
            "per_market": {"one_x_two": {"activations": 100, "failures": 20}},
        }
    }
    out = compute_reason_reliability(failure_metrics, alpha=2.0, beta=2.0)
    r1 = out["R1"]["global"]
    empirical_reliability = 1.0 - 20 / 100  # 0.8
    assert pytest.approx(empirical_reliability, rel=0.05) == r1["reliability"]


def test_deterministic_ordering_of_reasons_and_markets() -> None:
    """Keys for reasons and markets must be sorted deterministically."""
    failure_metrics = {
        "R2": {
            "global": {"activations": 10, "failures": 2},
            "per_market": {"gg_ng": {"activations": 5, "failures": 1}},
        },
        "R1": {
            "global": {"activations": 5, "failures": 1},
            "per_market": {"one_x_two": {"activations": 5, "failures": 1}},
        },
    }
    out = compute_reason_reliability(failure_metrics)
    reasons = list(out.keys())
    assert reasons == sorted(reasons)
    # Check per_market keys sorted for one reason
    markets = list(out["R1"]["per_market"].keys())
    assert markets == sorted(markets)


def test_empty_input_returns_empty() -> None:
    """Empty failure metrics -> empty reliability metrics."""
    out = compute_reason_reliability({})
    assert out == {}


def test_reason_reliability_for_report_includes_meta_and_sorted_metrics() -> None:
    """Wrapper includes meta and sorted reason_reliability block."""
    failure_metrics = {
        "R1": {
            "global": {"activations": 5, "failures": 1},
            "per_market": {"one_x_two": {"activations": 5, "failures": 1}},
        }
    }
    block = reason_reliability_for_report(failure_metrics)
    assert "reason_reliability" in block
    assert "meta" in block
    assert block["meta"]["method"] == "beta_smoothing"
    assert block["meta"]["alpha"] == DEFAULT_ALPHA
    assert block["meta"]["beta"] == DEFAULT_BETA

