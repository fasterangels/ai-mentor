"""
Unit tests for offline per-market threshold fitting for the decision engine policy.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.policies.decision_engine_policy import (  # type: ignore[import-error]
    DecisionPolicy,
)
from backend.policies.fit_decision_engine_policy import (  # type: ignore[import-error]
    FitConfig,
    fit_policy,
    fit_threshold_for_market,
)


def _precision_for_market(rows: List[Dict[str, object]], market: str, threshold: float) -> float:
    market_rows = [r for r in rows if r["market"] == market]
    if not market_rows:
        return 0.0
    go_rows = [r for r in market_rows if float(r["score"]) >= threshold]
    if not go_rows:
        return 0.0
    correct_go = sum(int(r["outcome"]) for r in go_rows)
    return correct_go / float(len(go_rows))


def test_fit_policy_per_market_and_default_improves_over_baseline() -> None:
    # Synthetic rows for markets A and B.
    rows: List[Dict[str, object]] = []

    # Market A: strong correlation, high scores much more likely correct.
    for _ in range(30):
        rows.append({"market": "A", "score": 0.9, "outcome": 1})
    for _ in range(10):
        rows.append({"market": "A", "score": 0.4, "outcome": 0})

    # Market B: weaker correlation, more noise.
    for _ in range(15):
        rows.append({"market": "B", "score": 0.8, "outcome": 1})
    for _ in range(15):
        rows.append({"market": "B", "score": 0.5, "outcome": 0})

    cfg = FitConfig(min_coverage=0.20, objective="precision", threshold_grid=None, version="v_test")
    policy: DecisionPolicy = fit_policy(rows, cfg)

    # Policy should contain thresholds for default, A and B.
    assert "default" in policy.thresholds
    assert "A" in policy.thresholds
    assert "B" in policy.thresholds

    for t in policy.thresholds.values():
        assert 0.0 <= t <= 1.0

    # Precision for market A at fitted threshold should be at least as good
    # as a naive baseline threshold of 0.55.
    baseline_precision = _precision_for_market(rows, "A", 0.55)
    fitted_precision = _precision_for_market(rows, "A", policy.thresholds["A"])
    assert fitted_precision >= baseline_precision


def test_tie_break_prefers_higher_coverage_then_higher_threshold() -> None:
    # All rows are correct; precision == 1.0 for any threshold below 1.0.
    rows = [
        {"market": "A", "score": 0.8, "outcome": 1},
        {"market": "A", "score": 0.8, "outcome": 1},
        {"market": "A", "score": 0.6, "outcome": 1},
        {"market": "A", "score": 0.6, "outcome": 1},
    ]

    # With this grid, both thresholds produce precision 1.0 but different coverage.
    cfg = FitConfig(
        min_coverage=0.0,
        objective="precision",
        threshold_grid=[0.6, 0.8],
        version="v_tie",
    )

    t = fit_threshold_for_market(rows, cfg)
    # 0.6 has higher coverage than 0.8, so it should be chosen.
    assert t == 0.6


def test_target_precision_max_coverage() -> None:
    # Synthetic rows for a single market A where:
    # - threshold 0.40: high coverage, low precision (~0.5)
    # - threshold 0.60: medium coverage, precision ~0.71
    # - threshold 0.70: lower coverage, precision ~0.60
    rows: List[Dict[str, object]] = []

    # 6 correct with high scores
    for _ in range(6):
        rows.append({"market": "A", "score": 0.8, "outcome": 1})
    # 4 incorrect at 0.7
    for _ in range(4):
        rows.append({"market": "A", "score": 0.7, "outcome": 0})
    # 4 correct at 0.6
    for _ in range(4):
        rows.append({"market": "A", "score": 0.6, "outcome": 1})
    # 6 incorrect at 0.4
    for _ in range(6):
        rows.append({"market": "A", "score": 0.4, "outcome": 0})

    cfg = FitConfig(
        min_coverage=0.20,
        objective="precision",
        threshold_grid=[0.4, 0.6, 0.7],
        target_precision=0.70,
        version="v_target",
    )

    t = fit_threshold_for_market(rows, cfg)
    # Only 0.6 meets target precision >= 0.70, so it should be chosen.
    assert t == 0.6


def test_target_precision_fallback_to_objective_when_impossible() -> None:
    rows = [
        {"market": "A", "score": 0.4, "outcome": 0},
        {"market": "A", "score": 0.5, "outcome": 0},
        {"market": "A", "score": 0.6, "outcome": 0},
        {"market": "A", "score": 0.7, "outcome": 1},
    ]

    base_cfg = FitConfig(
        min_coverage=0.0,
        objective="precision",
        threshold_grid=[0.4, 0.6, 0.7],
        target_precision=None,
        version="v_base",
    )
    base_t = fit_threshold_for_market(rows, base_cfg)

    target_cfg = FitConfig(
        min_coverage=0.0,
        objective="precision",
        threshold_grid=[0.4, 0.6, 0.7],
        target_precision=0.95,  # impossible to reach
        version="v_target_fallback",
    )
    target_t = fit_threshold_for_market(rows, target_cfg)

    # When target_precision is unattainable, fallback should match objective-based threshold.
    assert target_t == base_t

