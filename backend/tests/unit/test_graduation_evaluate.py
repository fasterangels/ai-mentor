"""
Unit tests for graduation evaluator (J1 Part A).
- Missing artifact -> FAIL criterion with clear detail
- Threshold boundary -> PASS/FAIL correct
- Deterministic ordering of criteria
- overall_pass is AND of all criterion passes
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from graduation.criteria_v1 import (
    DEFAULT_DECAY_MIN_REASON_CODES,
    DEFAULT_DELTA_COVERAGE_MIN_FIXTURES,
    DEFAULT_DELTA_PAYLOAD_MATCH_MIN_RATE,
    DEFAULT_STALENESS_MIN_REASON_CODES,
    DEFAULT_UNCERTAINTY_MIN_DECISIONS,
    DEFAULT_WORST_CASE_MIN_ROWS,
    CriterionResult,
    GraduationResult,
)
from graduation.evaluate import CRITERION_ORDER, evaluate_graduation


def test_missing_artifact_fails_criterion_with_clear_detail(tmp_path):
    """Empty reports_dir -> each criterion that needs an artifact fails with reason like 'artifact missing' or 'dir missing'."""
    result = evaluate_graduation(tmp_path)
    assert result.overall_pass is False
    # At least one criterion should mention missing path/artifact
    names_with_reason = [c.name for c in result.criteria if not c.pass_ and c.details]
    assert len(names_with_reason) >= 1
    for c in result.criteria:
        if not c.pass_:
            assert "reason" in c.details or "path" in c.details or "missing" in str(c.details).lower(), (
                f"Criterion {c.name} should have reason/path/missing in details: {c.details}"
            )


def test_delta_coverage_boundary_pass(tmp_path):
    """Exactly N fixtures with both deltas -> DELTA_COVERAGE PASS."""
    delta_dir = tmp_path / "delta_eval"
    delta_dir.mkdir(parents=True)
    N = DEFAULT_DELTA_COVERAGE_MIN_FIXTURES
    reports = [
        {"fixture_id": f"f{i}", "recorded_snapshot_id": "r1", "live_snapshot_id": "l1", "payload_match": True}
        for i in range(N)
    ]
    (delta_dir / "delta_eval_001.json").write_text(
        json.dumps({"reports": reports, "summary": {"complete": N, "total": N}}, indent=2),
        encoding="utf-8",
    )
    result = evaluate_graduation(tmp_path, delta_coverage_min=N)
    delta_cov = next(c for c in result.criteria if c.name == "DELTA_COVERAGE")
    assert delta_cov.pass_ is True
    assert delta_cov.details.get("fixtures_with_both_deltas") == N


def test_delta_coverage_boundary_fail(tmp_path):
    """N-1 fixtures with both deltas -> DELTA_COVERAGE FAIL."""
    delta_dir = tmp_path / "delta_eval"
    delta_dir.mkdir(parents=True)
    N = DEFAULT_DELTA_COVERAGE_MIN_FIXTURES
    reports = [
        {"fixture_id": f"f{i}", "recorded_snapshot_id": "r1", "live_snapshot_id": "l1", "payload_match": True}
        for i in range(N - 1)
    ]
    (delta_dir / "delta_eval_001.json").write_text(
        json.dumps({"reports": reports, "summary": {"complete": N - 1, "total": N - 1}}, indent=2),
        encoding="utf-8",
    )
    result = evaluate_graduation(tmp_path, delta_coverage_min=N)
    delta_cov = next(c for c in result.criteria if c.name == "DELTA_COVERAGE")
    assert delta_cov.pass_ is False
    assert delta_cov.details.get("fixtures_with_both_deltas") == N - 1


def test_delta_payload_match_boundary_pass(tmp_path):
    """payload_match rate exactly 0.95 -> DELTA_PAYLOAD_MATCH_RATE PASS."""
    delta_dir = tmp_path / "delta_eval"
    delta_dir.mkdir(parents=True)
    reports = []
    for i in range(100):
        reports.append({
            "fixture_id": f"f{i}",
            "recorded_snapshot_id": "r",
            "live_snapshot_id": "l",
            "payload_match": i < 95,
        })
    (delta_dir / "delta_eval_001.json").write_text(
        json.dumps({"reports": reports, "summary": {"complete": 100, "total": 100}}, indent=2),
        encoding="utf-8",
    )
    result = evaluate_graduation(tmp_path, delta_payload_match_min=0.95)
    pm = next(c for c in result.criteria if c.name == "DELTA_PAYLOAD_MATCH_RATE")
    assert pm.pass_ is True
    assert pm.details.get("payload_match_rate") == 0.95


def test_delta_payload_match_boundary_fail(tmp_path):
    """payload_match rate below 0.95 -> DELTA_PAYLOAD_MATCH_RATE FAIL."""
    delta_dir = tmp_path / "delta_eval"
    delta_dir.mkdir(parents=True)
    reports = [
        {"fixture_id": "f1", "recorded_snapshot_id": "r", "live_snapshot_id": "l", "payload_match": False},
        {"fixture_id": "f2", "recorded_snapshot_id": "r", "live_snapshot_id": "l", "payload_match": True},
    ]
    (delta_dir / "delta_eval_001.json").write_text(
        json.dumps({"reports": reports, "summary": {"complete": 2, "total": 2}}, indent=2),
        encoding="utf-8",
    )
    result = evaluate_graduation(tmp_path, delta_payload_match_min=0.95)
    pm = next(c for c in result.criteria if c.name == "DELTA_PAYLOAD_MATCH_RATE")
    assert pm.pass_ is False
    assert pm.details.get("payload_match_rate") == 0.5


def test_deterministic_ordering_of_criteria(tmp_path):
    """Criteria list order matches CRITERION_ORDER."""
    result = evaluate_graduation(tmp_path)
    names = [c.name for c in result.criteria]
    assert names == CRITERION_ORDER


def test_overall_pass_is_and_of_all_passes(tmp_path):
    """overall_pass is True only when every criterion passes."""
    # Build minimal artifacts so all criteria can pass (or use high thresholds to force all pass with minimal data)
    delta_dir = tmp_path / "delta_eval"
    delta_dir.mkdir(parents=True)
    N = 60
    reports = [
        {"fixture_id": f"f{i}", "recorded_snapshot_id": "r", "live_snapshot_id": "l", "payload_match": True}
        for i in range(N)
    ]
    (delta_dir / "delta_eval_001.json").write_text(
        json.dumps({"reports": reports, "summary": {"complete": N, "total": N}}, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "staleness_eval").mkdir(parents=True)
    rows = [{"reason_code": f"R{i}", "total": 10} for i in range(25)]
    (tmp_path / "staleness_eval" / "staleness_metrics_by_reason.json").write_text(
        json.dumps({"rows": rows}, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "decay_fit").mkdir(parents=True)
    params = [{"reason_code": f"R{i}", "fit_quality": {"bands_with_support": 3}} for i in range(25)]
    (tmp_path / "decay_fit" / "reason_decay_params.json").write_text(
        json.dumps({"params": params}, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "uncertainty_shadow_decisions.json").write_text(
        json.dumps({"decisions": [{"id": i} for i in range(250)]}, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "replay_scenarios" / "late_data").mkdir(parents=True)
    (tmp_path / "replay_scenarios" / "late_data" / "late_data_summary.json").write_text(
        json.dumps({"accuracy_delta_24h": -0.05, "refusal_delta_24h": 0.0}, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "worst_case_errors_top.json").write_text(
        json.dumps({"rows": [{"reason_code": f"R{i}"} for i in range(25)]}, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "refusal_optimization_best_overall.json").write_text(json.dumps({}), encoding="utf-8")
    (tmp_path / "refusal_optimization_grid_summary.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    result = evaluate_graduation(tmp_path)
    all_passed = all(c.pass_ for c in result.criteria)
    assert result.overall_pass == all_passed
    assert result.overall_pass is True

    # Break one criterion -> overall_pass False
    (tmp_path / "worst_case_errors_top.json").write_text(json.dumps({"rows": []}), encoding="utf-8")
    result2 = evaluate_graduation(tmp_path, worst_case_min_rows=DEFAULT_WORST_CASE_MIN_ROWS)
    assert result2.overall_pass is False
    worst = next(c for c in result2.criteria if c.name == "WORST_CASE_VISIBILITY")
    assert worst.pass_ is False
