"""
Unit tests for worst-case error scoring (I2 Part A).
Deterministic: scoring correctness, confidence weighting, uncertainty penalty, stable sort.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from evaluation.worst_case_errors import (
    EvaluatedDecision,
    UncertaintyShadow,
    compute_worst_case_report,
    worst_case_score,
)


def _decision(
    fixture_id: str = "f1",
    market: str = "one_x_two",
    prediction: str = "home",
    outcome: str = "FAILURE",
    original_confidence: float = 0.7,
    would_refuse: bool = False,
    signals: list | None = None,
    snapshot_ids: list | None = None,
    snapshot_type: str | None = None,
) -> EvaluatedDecision:
    shadow = UncertaintyShadow(would_refuse=would_refuse, triggered_uncertainty_signals=signals) if (would_refuse or signals) else None
    return EvaluatedDecision(
        fixture_id=fixture_id,
        market=market,
        prediction=prediction,
        outcome=outcome,
        original_confidence=original_confidence,
        uncertainty_shadow=shadow,
        snapshot_ids=snapshot_ids,
        snapshot_type=snapshot_type,
    )


def test_scoring_correct_vs_incorrect() -> None:
    """Correct (SUCCESS) => score 0; incorrect (FAILURE) => score > 0."""
    correct = _decision(outcome="SUCCESS", original_confidence=0.9)
    incorrect = _decision(outcome="FAILURE", original_confidence=0.5)
    assert worst_case_score(correct) == 0.0
    assert worst_case_score(incorrect) == 1.5  # base * (1 + 0.5)


def test_confidence_weighting_applied() -> None:
    """Higher confidence on incorrect prediction => higher score (same base)."""
    low = _decision(outcome="FAILURE", original_confidence=0.5)
    high = _decision(outcome="FAILURE", original_confidence=0.9)
    assert worst_case_score(low) == 1.5
    assert worst_case_score(high) == 1.9
    assert worst_case_score(high) > worst_case_score(low)


def test_uncertainty_penalty_deterministic() -> None:
    """Optional +0.25 when would_refuse is True; no penalty when False or no shadow."""
    no_shadow = _decision(outcome="FAILURE", original_confidence=0.6, would_refuse=False)
    refuse = _decision(outcome="FAILURE", original_confidence=0.6, would_refuse=True)
    assert worst_case_score(no_shadow) == 1.6
    assert worst_case_score(refuse) == 1.85
    # Correct prediction: base=0 so penalty has no effect
    correct_refuse = _decision(outcome="SUCCESS", original_confidence=0.6, would_refuse=True)
    assert worst_case_score(correct_refuse) == 0.0


def test_stable_sort_score_desc_then_fixture_id() -> None:
    """Report rows sorted by score desc, then fixture_id ascending for tie-break."""
    decisions = [
        _decision(fixture_id="f2", outcome="FAILURE", original_confidence=0.5),   # 1.5
        _decision(fixture_id="f1", outcome="FAILURE", original_confidence=0.5),   # 1.5
        _decision(fixture_id="f3", outcome="SUCCESS", original_confidence=0.9),   # 0
        _decision(fixture_id="f0", outcome="FAILURE", original_confidence=0.8),   # 1.8
    ]
    report = compute_worst_case_report(decisions)
    rows = report.rows
    assert len(rows) == 4
    # f0: 1.8, then f1/f2 tie 1.5 (fixture_id f1 < f2), then f3: 0
    assert rows[0].fixture_id == "f0" and rows[0].worst_case_score == 1.8
    assert rows[1].fixture_id == "f1" and rows[1].worst_case_score == 1.5
    assert rows[2].fixture_id == "f2" and rows[2].worst_case_score == 1.5
    assert rows[3].fixture_id == "f3" and rows[3].worst_case_score == 0.0


def test_report_triggered_signals_and_snapshot_ids() -> None:
    """WorstCaseRow includes triggered_uncertainty_signals, snapshot_ids, and snapshot_type when provided."""
    d = _decision(
        fixture_id="fx",
        outcome="FAILURE",
        would_refuse=True,
        signals=["stale", "delta"],
        snapshot_ids=["s1", "s2"],
        snapshot_type="live_shadow",
    )
    report = compute_worst_case_report([d])
    assert len(report.rows) == 1
    r = report.rows[0]
    assert r.triggered_uncertainty_signals == ["stale", "delta"]
    assert r.snapshot_ids == ["s1", "s2"]
    assert r.snapshot_type == "live_shadow"


def test_report_computed_at_utc_set() -> None:
    """Report has computed_at_utc (set by default or passed)."""
    report = compute_worst_case_report([])
    assert report.computed_at_utc is not None
    assert report.computed_at_utc.tzinfo is not None


def test_top_n_truncates() -> None:
    """When top_n is set, only that many rows returned."""
    decisions = [
        _decision(fixture_id=f"f{i}", outcome="FAILURE", original_confidence=0.5 + i * 0.1)
        for i in range(5)
    ]
    report = compute_worst_case_report(decisions, top_n=2)
    assert len(report.rows) == 2
