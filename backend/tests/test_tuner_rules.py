"""Tuner: deterministic proposal from fixed evaluation input; guardrails enforced."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def test_tuner_deterministic_proposal():
    """Same evaluation report => same proposal (no random)."""
    from policy.tuner import run_tuner
    from policy.policy_store import default_policy

    report = {
        "overall": {"total_snapshots": 100, "resolved_snapshots": 100},
        "per_market_accuracy": {
            "one_x_two": {
                "success_count": 30,
                "failure_count": 20,
                "neutral_count": 50,
                "accuracy": 0.6,
                "confidence_bands": {
                    "0.55-0.60": {
                        "success_count": 5,
                        "failure_count": 15,
                        "neutral_count": 2,
                        "accuracy": 0.25,
                    },
                },
            },
            "over_under_25": {"success_count": 40, "failure_count": 30, "neutral_count": 30, "accuracy": 0.57},
            "gg_ng": {"success_count": 35, "failure_count": 25, "neutral_count": 40, "accuracy": 0.58},
        },
        "reason_effectiveness": {},
    }
    p1 = run_tuner(report)
    p2 = run_tuner(report)
    assert p1.evaluation_report_checksum == p2.evaluation_report_checksum
    assert p1.proposed_policy.markets["one_x_two"].min_confidence == p2.proposed_policy.markets["one_x_two"].min_confidence
    # Band 0.55-0.60 has failure_rate 15/20 = 0.75 > 0.65, n=22 (5+15+2) which is < 30, so no bump. Add more to get bump.
    assert len(p1.diffs) == len(p2.diffs)


def test_tuner_guardrails_enforced():
    """Guardrails: min_confidence delta <= 0.05; dampening decrease <= 25%."""
    from policy.tuner import run_tuner

    report = {
        "overall": {"total_snapshots": 200, "resolved_snapshots": 200},
        "per_market_accuracy": {
            "one_x_two": {
                "success_count": 10,
                "failure_count": 30,
                "neutral_count": 0,
                "accuracy": 0.25,
                "confidence_bands": {
                    "0.55-0.60": {"success_count": 2, "failure_count": 28, "neutral_count": 0, "accuracy": 0.067},
                },
            },
            "over_under_25": {"success_count": 40, "failure_count": 30, "neutral_count": 30, "accuracy": 0.57},
            "gg_ng": {"success_count": 35, "failure_count": 25, "neutral_count": 40, "accuracy": 0.58},
        },
        "reason_effectiveness": {
            "SOME_REASON": {
                "one_x_two": {"success": 5, "failure": 40, "neutral": 0, "success_rate": 0.111},
                "over_under_25": {"success": 3, "failure": 35, "neutral": 0, "success_rate": 0.079},
                "gg_ng": {"success": 2, "failure": 38, "neutral": 0, "success_rate": 0.05},
            },
        },
    }
    proposal = run_tuner(report)
    for name, passed, msg in proposal.guardrails_results:
        if "min_confidence" in name:
            assert passed, f"min_confidence guardrail should pass: {msg}"
        if "dampening" in name:
            assert passed, f"dampening guardrail should pass: {msg}"


def test_tuner_proposal_includes_checksum():
    """Proposal includes evaluation_report_checksum."""
    from policy.tuner import run_tuner

    report = {"overall": {}, "per_market_accuracy": {}, "reason_effectiveness": {}}
    proposal = run_tuner(report)
    assert isinstance(proposal.evaluation_report_checksum, str)
    assert len(proposal.evaluation_report_checksum) == 64  # sha256 hex
