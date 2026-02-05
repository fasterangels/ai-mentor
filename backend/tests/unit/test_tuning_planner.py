"""
Unit tests for tuning_planner: determinism given fixed quality_audit and policy.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from policy.policy_model import MarketPolicy, Policy, PolicyVersion, ReasonPolicy
from policy.tuning_planner import plan_from_quality_audit, replay_regression


def _fixed_policy() -> Policy:
    return Policy(
        meta=PolicyVersion(
            version="v0-test",
            created_at_utc=datetime(2025, 1, 1, 0, 0, 0),
            notes="Test",
        ),
        markets={
            "one_x_two": MarketPolicy(min_confidence=0.62),
            "over_under_25": MarketPolicy(min_confidence=0.62),
            "gg_ng": MarketPolicy(min_confidence=0.62),
        },
        reasons={
            "R1": ReasonPolicy(reason_code="R1", dampening_factor=1.0),
        },
    )


def _fixed_quality_audit() -> dict:
    """Fixed quality_audit report that yields deterministic proposals."""
    return {
        "summary": {"run_count": 50},
        "suggestions": {
            "confidence_band_adjustments": [
                {
                    "market": "one_x_two",
                    "band": "0.60-0.65",
                    "predicted_confidence": 0.625,
                    "empirical_accuracy": 0.45,
                    "deviation": 0.175,
                    "count": 15,
                    "suggestion": "consider shifting band or threshold",
                },
            ],
            "dampening_candidates": [
                {
                    "reason_code": "R1",
                    "decayed_contribution": -0.2,
                    "win_count": 2,
                    "loss_count": 5,
                    "suggestion": "consider dampening weight for this reason",
                },
            ],
        },
        "confidence_calibration": {},
    }


def test_plan_from_quality_audit_deterministic() -> None:
    """Same quality_audit and policy produce identical proposals (determinism)."""
    audit = _fixed_quality_audit()
    policy = _fixed_policy()
    r1 = plan_from_quality_audit(audit, current_policy=policy)
    r2 = plan_from_quality_audit(audit, current_policy=policy)
    assert r1["proposals"] == r2["proposals"]
    assert r1["proposal_count"] == r2["proposal_count"]
    assert r1["guardrails_passed"] == r2["guardrails_passed"]
    assert r1["proposed_policy_snapshot"]["markets"] == r2["proposed_policy_snapshot"]["markets"]
    # Normalize proposal order for comparison (order might be stable but exclude volatile keys like reason text)
    for i, (p1, p2) in enumerate(zip(r1["proposals"], r2["proposals"])):
        assert p1["type"] == p2["type"]
        if p1["type"] == "min_confidence":
            assert p1["market"] == p2["market"] and p1["old_val"] == p2["old_val"] and p1["new_val"] == p2["new_val"]
        else:
            assert p1["reason_code"] == p2["reason_code"] and p1["old_val"] == p2["old_val"] and p1["new_val"] == p2["new_val"]


def test_plan_from_quality_audit_produces_proposals_from_fixture() -> None:
    """Fixed audit with miscalibration and dampening candidate yields at least one proposal."""
    audit = _fixed_quality_audit()
    policy = _fixed_policy()
    result = plan_from_quality_audit(audit, current_policy=policy)
    assert result["proposal_count"] >= 1
    assert "proposals" in result
    assert "proposed_policy_snapshot" in result
    assert "guardrails_passed" in result


def test_replay_regression_deterministic() -> None:
    """Same records and proposed_min_confidence produce identical replay result."""
    records = [
        {
            "market_outcomes": {"one_x_two": "SUCCESS", "over_under_25": "FAILURE", "gg_ng": "SUCCESS"},
            "predictions": [
                {"market": "1X2", "confidence": 0.65, "pick": "home"},
                {"market": "OU25", "confidence": 0.60, "pick": "over"},
                {"market": "GGNG", "confidence": 0.70, "pick": "yes"},
            ],
        },
        {
            "market_outcomes": {"one_x_two": "FAILURE", "over_under_25": "SUCCESS", "gg_ng": "UNRESOLVED"},
            "predictions": [
                {"market": "1X2", "confidence": 0.62, "pick": "away"},
                {"market": "OU25", "confidence": 0.68, "pick": "under"},
            ],
        },
    ]
    proposed = {"one_x_two": 0.64, "over_under_25": 0.62, "gg_ng": 0.65}
    r1 = replay_regression(records, proposed, coverage_drop_threshold=0.10, accuracy_drop_threshold=0.05)
    r2 = replay_regression(records, proposed, coverage_drop_threshold=0.10, accuracy_drop_threshold=0.05)
    assert r1["baseline_coverage_pct"] == r2["baseline_coverage_pct"]
    assert r1["proposed_coverage_pct"] == r2["proposed_coverage_pct"]
    assert r1["coverage_drop"] == r2["coverage_drop"]
    assert r1["baseline_accuracy"] == r2["baseline_accuracy"]
    assert r1["proposed_accuracy"] == r2["proposed_accuracy"]
    assert r1["blocked"] == r2["blocked"]
    assert r1["reasons"] == r2["reasons"]


def test_replay_regression_blocks_on_coverage_drop() -> None:
    """When proposed min_confidence excludes many predictions, coverage drop can exceed threshold."""
    # Baseline: 3 markets * 2 records = 6 slots; all at 0.62 so all covered
    records = [
        {
            "market_outcomes": {"one_x_two": "SUCCESS", "over_under_25": "SUCCESS", "gg_ng": "SUCCESS"},
            "predictions": [
                {"market": "1X2", "confidence": 0.62, "pick": "home"},
                {"market": "OU25", "confidence": 0.62, "pick": "over"},
                {"market": "GGNG", "confidence": 0.62, "pick": "yes"},
            ],
        },
        {
            "market_outcomes": {"one_x_two": "SUCCESS", "over_under_25": "SUCCESS", "gg_ng": "SUCCESS"},
            "predictions": [
                {"market": "1X2", "confidence": 0.62, "pick": "away"},
                {"market": "OU25", "confidence": 0.62, "pick": "under"},
                {"market": "GGNG", "confidence": 0.62, "pick": "no"},
            ],
        },
    ]
    # Propose very high bar: nothing passes -> proposed_covered = 0 -> coverage_drop large
    proposed = {"one_x_two": 0.99, "over_under_25": 0.99, "gg_ng": 0.99}
    result = replay_regression(records, proposed, coverage_drop_threshold=0.10, accuracy_drop_threshold=0.05)
    assert result["blocked"] is True
    assert any("coverage_drop" in r for r in result["reasons"])
