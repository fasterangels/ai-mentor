"""
Unit tests for Go/No-Go decision (J3 Part A).
- Graduation PASS -> GO
- Graduation FAIL -> NO_GO + failed_criteria populated
- Deterministic output ordering
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from graduation.criteria_v1 import CriterionResult, GraduationResult
from graduation.go_no_go import GoNoGoDecision, compute_go_no_go


def _result_pass() -> GraduationResult:
    return GraduationResult(
        overall_pass=True,
        criteria=[
            CriterionResult("DELTA_COVERAGE", True, {"fixtures_with_both_deltas": 60, "min_required": 50}),
            CriterionResult("DELTA_PAYLOAD_MATCH_RATE", True, {"payload_match_rate": 0.96, "min_required": 0.95}),
        ],
        computed_at_utc=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def _result_fail() -> GraduationResult:
    return GraduationResult(
        overall_pass=False,
        criteria=[
            CriterionResult("DELTA_COVERAGE", True, {"fixtures_with_both_deltas": 50, "min_required": 50}),
            CriterionResult("DELTA_PAYLOAD_MATCH_RATE", False, {"reason": "below threshold", "payload_match_rate": 0.9, "min_required": 0.95}),
            CriterionResult("STALENESS_OBSERVABILITY", False, {"reason": "artifact missing", "path": "/x"}),
        ],
        computed_at_utc=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_graduation_pass_go() -> None:
    """When graduation overall_pass is True, decision is GO."""
    result = _result_pass()
    decision = compute_go_no_go(result)
    assert decision.decision == "GO"
    assert decision.failed_criteria == []
    assert decision.schema_version == 1


def test_graduation_fail_no_go_failed_criteria_populated() -> None:
    """When graduation overall_pass is False, decision is NO_GO and failed_criteria list has name + details."""
    result = _result_fail()
    decision = compute_go_no_go(result)
    assert decision.decision == "NO_GO"
    assert len(decision.failed_criteria) == 2
    names = [f["name"] for f in decision.failed_criteria]
    assert "DELTA_PAYLOAD_MATCH_RATE" in names
    assert "STALENESS_OBSERVABILITY" in names
    for f in decision.failed_criteria:
        assert "name" in f and "details" in f
        assert isinstance(f["details"], dict)


def test_deterministic_output_ordering() -> None:
    """Failed criteria appear in same order as in graduation result; decision fields stable."""
    result = _result_fail()
    decision = compute_go_no_go(result)
    # Order of failed_criteria must follow order of criteria in result
    failed_names_order = [f["name"] for f in decision.failed_criteria]
    expected_order = [c.name for c in result.criteria if not c.pass_]
    assert failed_names_order == expected_order

    # Decision has all required fields in deterministic structure
    assert decision.schema_version == 1
    assert decision.decision in ("GO", "NO_GO")
    assert decision.decision_time_utc is not None
    assert isinstance(decision.failed_criteria, list)
    assert isinstance(decision.warnings, list)


def test_go_with_boundary_warning() -> None:
    """When GO and a criterion passed at exact minimum, warnings can be derived."""
    result = GraduationResult(
        overall_pass=True,
        criteria=[
            CriterionResult("DELTA_COVERAGE", True, {"fixtures_with_both_deltas": 50, "min_required": 50}),
        ],
        computed_at_utc=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    decision = compute_go_no_go(result)
    assert decision.decision == "GO"
    assert any("DELTA_COVERAGE" in w and "minimum" in w for w in decision.warnings)
