"""
Unit tests for refusal threshold grid search (I3 Part A).
Deterministic: grid result, tie-breakers, refuse rule, objective.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from optimization.refusal_shadow import (
    ALPHA,
    BestThresholds,
    ShadowDecision,
    STALE_BANDS,
    effective_confidence_grid,
    grid_search_best_thresholds,
    would_refuse,
)


def _decision(
    effective_confidence: float = 0.5,
    age_band: str = "1-3d",
    outcome: str = "SUCCESS",
    market: str | None = "one_x_two",
) -> ShadowDecision:
    return ShadowDecision(
        effective_confidence=effective_confidence,
        age_band=age_band,
        outcome=outcome,
        market=market,
    )


def test_grid_search_deterministic_on_synthetic() -> None:
    """Grid search returns deterministic best thresholds on synthetic dataset."""
    decisions = [
        _decision(0.2, "7d+", "FAILURE"),
        _decision(0.2, "7d+", "FAILURE"),
        _decision(0.8, "7d+", "SUCCESS"),
        _decision(0.3, "3-7d", "SUCCESS"),
        _decision(0.4, "3-7d", "SUCCESS"),
        _decision(0.5, "1-3d", "SUCCESS"),
        _decision(0.5, "1-3d", "SUCCESS"),
        _decision(0.6, "6-24h", "SUCCESS"),
        _decision(0.6, "6-24h", "FAILURE"),
        _decision(0.7, "6-24h", "FAILURE"),
    ]
    result = grid_search_best_thresholds(decisions)
    assert None in result
    best = result[None]
    assert isinstance(best, BestThresholds)
    assert 0.10 <= best.effective_confidence_threshold <= 0.90
    assert best.stale_band_threshold in STALE_BANDS
    assert 0 <= best.refusal_rate <= 1
    assert 0 <= best.accuracy_on_non_refused <= 1
    assert best.support_total == 10
    result2 = grid_search_best_thresholds(decisions)
    assert result2[None].effective_confidence_threshold == result[None].effective_confidence_threshold
    assert result2[None].stale_band_threshold == result[None].stale_band_threshold
    assert result2[None].safety_score == result[None].safety_score


def test_tie_breakers_deterministic() -> None:
    """Among ties, pick lower refusal_rate then higher accuracy then lowest thresholds."""
    decisions = [
        _decision(0.5, "6-24h", "SUCCESS"),
        _decision(0.5, "6-24h", "FAILURE"),
    ]
    result = grid_search_best_thresholds(decisions)
    best = result[None]
    assert best.effective_confidence_threshold == min(effective_confidence_grid())
    assert best.stale_band_threshold == STALE_BANDS[0]


def test_refusal_rule_correctness() -> None:
    """would_refuse is True only when age_band >= stale_band_threshold AND effective_confidence < eff_conf_threshold."""
    d = ShadowDecision(effective_confidence=0.4, age_band="3-7d", outcome="SUCCESS")
    assert would_refuse(d, 0.5, "7d+") is False
    assert would_refuse(d, 0.5, "3-7d") is True
    assert would_refuse(d, 0.30, "3-7d") is False
    d2 = ShadowDecision(effective_confidence=0.4, age_band="6-24h", outcome="SUCCESS")
    assert would_refuse(d2, 0.5, "6-24h") is True


def test_objective_computed_correctly() -> None:
    """safety_score = accuracy_on_non_refused - ALPHA * refusal_rate; accuracy ignores neutrals."""
    decisions = [
        _decision(0.2, "7d+", "FAILURE"),
        _decision(0.2, "7d+", "FAILURE"),
        _decision(0.9, "6-24h", "SUCCESS"),
        _decision(0.9, "6-24h", "FAILURE"),
    ]
    result = grid_search_best_thresholds(decisions)
    best = result[None]
    assert best.support_total == 4
    assert best.support_refused + best.support_non_refused == 4
    expected_safety = round(best.accuracy_on_non_refused - ALPHA * best.refusal_rate, 4)
    assert best.safety_score == expected_safety


def test_effective_confidence_grid() -> None:
    """Grid is 0.10 to 0.90 in 0.05 steps (17 values)."""
    grid = effective_confidence_grid()
    assert len(grid) == 17
    assert grid[0] == 0.10
    assert grid[-1] == 0.90
    for i in range(len(grid) - 1):
        assert round(grid[i + 1] - grid[i], 2) == 0.05


def test_per_market_results() -> None:
    """grid_search_best_thresholds returns per-market and overall when markets list provided."""
    decisions = [
        _decision(0.3, "1-3d", "SUCCESS", "one_x_two"),
        _decision(0.5, "1-3d", "FAILURE", "one_x_two"),
        _decision(0.4, "7d+", "SUCCESS", "over_under_25"),
    ]
    result = grid_search_best_thresholds(decisions, markets=["one_x_two", "over_under_25"])
    assert None in result
    assert "one_x_two" in result
    assert "over_under_25" in result
    assert result["one_x_two"].support_total == 2
    assert result["over_under_25"].support_total == 1
