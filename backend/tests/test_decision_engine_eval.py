"""
Unit tests for Decision Engine evaluation helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.evaluation.decision_engine_eval import (  # type: ignore[import-error]
    build_reliability_table_from_reason_reliability,
    evaluate_decision_engine,
)


def test_build_reliability_table_prefers_per_market_and_falls_back_to_global() -> None:
    reason_reliability = {
        "global": {
            "R1": 0.8,
            "R2": 0.7,
        },
        "per_market": {
            "one_x_two": {
                "R1": 0.9,  # overrides global
            },
            # "gg_ng" intentionally missing R1/R2 to test fallback
            "gg_ng": {},
        },
    }

    table = build_reliability_table_from_reason_reliability(reason_reliability)

    # Per-market override wins
    assert table["one_x_two"]["R1"] == 0.9
    # Fallback to global when missing
    assert table["one_x_two"]["R2"] == 0.7
    assert table["gg_ng"]["R1"] == 0.8
    assert table["gg_ng"]["R2"] == 0.7


def test_build_reliability_table_uses_default_market_when_only_global() -> None:
    reason_reliability = {
        "global": {
            "R1": 0.5,
        },
        "per_market": {},
    }

    table = build_reliability_table_from_reason_reliability(reason_reliability)
    assert "default" in table
    assert table["default"]["R1"] == 0.5


def test_evaluate_decision_engine_basic_aggregation() -> None:
    reason_reliability = {
        "global": {},
        "per_market": {
            "default": {
                "R_GOOD": 0.9,
                "R_BAD": 0.2,
            }
        },
    }

    predictions = [
        {
            "id": "p1",
            "market": "default",
            "confidence": 0.9,
            "reason_codes": ["R_GOOD"],
        },
        {
            "id": "p2",
            "market": "default",
            "confidence": 0.3,
            "reason_codes": ["R_GOOD"],
        },
        {
            "id": "p3",
            "market": "default",
            "confidence": 0.8,
            "reason_codes": ["R_BAD"],  # low reliability
        },
    ]

    metrics = evaluate_decision_engine(predictions, reason_reliability)

    summary = metrics["summary"]
    assert summary["n"] == 3
    assert summary["go"] + summary["no_go"] == 3
    assert 0.0 <= summary["go_rate"] <= 1.0

    flag_counts = metrics["flag_counts"]
    # At least these failure modes should appear across the small set.
    assert "low_confidence" in flag_counts
    assert "low_reliability_reason_active" in flag_counts

    per_market = metrics["per_market"]
    assert "default" in per_market
    assert per_market["default"]["n"] == 3

    # Examples should be in input order and at most 20
    examples = metrics["examples"]
    assert [e["id"] for e in examples] == ["p1", "p2", "p3"]
    assert len(examples) == 3

