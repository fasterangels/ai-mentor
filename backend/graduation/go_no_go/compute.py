"""
Compute Go/No-Go decision from J1 GraduationResult.
Deterministic: pure function of graduation result. No automation, no behavior change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ..criteria_v1 import CriterionResult, GraduationResult

from .model import GoNoGoDecision


def _failed_criteria_list(criteria: List[CriterionResult]) -> List[Dict[str, Any]]:
    """Build deterministic list of failed criterion name + details (stable order)."""
    out: List[Dict[str, Any]] = []
    for c in criteria:
        if not c.pass_:
            out.append({"name": c.name, "details": dict(c.details)})
    return out


def _warnings_from_criteria(criteria: List[CriterionResult]) -> List[str]:
    """
    Derive optional warnings from criterion details only (no new heuristics).
    When a criterion passed but is at boundary (actual == min_required), add a warning.
    """
    warnings: List[str] = []
    for c in criteria:
        if not c.pass_:
            continue
        d = c.details
        # Boundary: fixtures_with_both_deltas == min_required
        if "fixtures_with_both_deltas" in d and "min_required" in d:
            if d.get("fixtures_with_both_deltas") == d.get("min_required"):
                warnings.append(f"{c.name} at minimum required fixtures ({d['min_required']})")
        # Boundary: payload_match_rate == min_required
        elif "payload_match_rate" in d and "min_required" in d:
            if d.get("payload_match_rate") == d.get("min_required"):
                warnings.append(f"{c.name} at minimum required rate ({d['min_required']})")
        # Other numeric boundaries: reason_codes_with_support, etc.
        elif "reason_codes_with_support" in d and "min_required" in d:
            if d.get("reason_codes_with_support") == d.get("min_required"):
                warnings.append(f"{c.name} at minimum required count ({d['min_required']})")
        elif "reason_codes_with_fit" in d and "min_required" in d:
            if d.get("reason_codes_with_fit") == d.get("min_required"):
                warnings.append(f"{c.name} at minimum required count ({d['min_required']})")
        elif "decisions_count" in d and "min_required" in d:
            if d.get("decisions_count") == d.get("min_required"):
                warnings.append(f"{c.name} at minimum required decisions ({d['min_required']})")
        elif "rows_count" in d and "min_required" in d:
            if d.get("rows_count") == d.get("min_required"):
                warnings.append(f"{c.name} at minimum required rows ({d['min_required']})")
    return warnings


def compute_go_no_go(
    graduation_result: GraduationResult,
    referenced_graduation_result_path: str | None = None,
    decision_time_utc: datetime | None = None,
) -> GoNoGoDecision:
    """
    Compute Go/No-Go decision from J1 graduation result.
    PASS -> GO; FAIL -> NO_GO. Deterministic; no automation.
    """
    if decision_time_utc is None:
        decision_time_utc = datetime.now(timezone.utc)
    if decision_time_utc.tzinfo is None:
        decision_time_utc = decision_time_utc.replace(tzinfo=timezone.utc)

    if graduation_result.overall_pass:
        decision = "GO"
        failed_criteria = []
        warnings = _warnings_from_criteria(graduation_result.criteria)
    else:
        decision = "NO_GO"
        failed_criteria = _failed_criteria_list(graduation_result.criteria)
        warnings = []

    return GoNoGoDecision(
        schema_version=1,
        decision=decision,
        decision_time_utc=decision_time_utc,
        graduation_ref=referenced_graduation_result_path,
        failed_criteria=failed_criteria,
        warnings=warnings,
    )
