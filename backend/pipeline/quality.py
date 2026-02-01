from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .types import QualityReport


def check_freshness(
    fetched_at_utc: str, window_hours: int
) -> tuple[bool, float]:
    """Check if data is fresh within the window.

    Returns:
        Tuple of (is_fresh, freshness_score 0.0-1.0)
    """
    try:
        fetched = datetime.fromisoformat(fetched_at_utc.replace("Z", "+00:00"))
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_hours = (now - fetched).total_seconds() / 3600

        is_fresh = age_hours <= window_hours
        # Score decreases linearly from 1.0 at 0h to 0.0 at window_hours
        freshness_score = max(0.0, 1.0 - (age_hours / window_hours))

        return is_fresh, freshness_score
    except (ValueError, AttributeError):
        return False, 0.0


def check_completeness(data: Dict[str, Any], required_fields: List[str]) -> tuple[bool, float]:
    """Check if required fields are present in data.

    Returns:
        Tuple of (is_complete, completeness_score 0.0-1.0)
    """
    if not data:
        return False, 0.0

    present = sum(1 for field in required_fields if field in data)
    total = len(required_fields)
    score = present / total if total > 0 else 0.0
    is_complete = present == total

    return is_complete, score


def assess_quality(
    payloads: List[Dict[str, Any]],
    window_hours: int,
    required_fields: List[str],
) -> QualityReport:
    """Assess quality of collected payloads.

    Args:
        payloads: List of normalized payload dicts
        window_hours: Expected freshness window
        required_fields: Required fields for completeness check

    Returns:
        QualityReport with passed status, score, and flags
    """
    flags: List[str] = []
    scores: List[float] = []

    if len(payloads) == 0:
        flags.append("NO_SOURCES_AVAILABLE")
        return QualityReport(passed=False, score=0.0, flags=flags)

    # Check source count (minimum 1, TODO: raise threshold later)
    if len(payloads) < 1:
        flags.append("INSUFFICIENT_SOURCES")
        return QualityReport(passed=False, score=0.0, flags=flags)

    # Check freshness for each payload
    freshness_scores = []
    for payload in payloads:
        fetched_at = payload.get("fetched_at_utc", "")
        is_fresh, freshness_score = check_freshness(fetched_at, window_hours)
        freshness_scores.append(freshness_score)
        if not is_fresh:
            flags.append("STALE_DATA")

    # Check completeness for each payload
    completeness_scores = []
    for payload in payloads:
        data = payload.get("data", {})
        is_complete, completeness_score = check_completeness(data, required_fields)
        completeness_scores.append(completeness_score)
        if not is_complete:
            flags.append("INCOMPLETE_DATA")

    # Overall quality score: average of freshness and completeness
    avg_freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0.0
    avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
    overall_score = (avg_freshness + avg_completeness) / 2.0

    # Quality gate: passed if score >= 0.5 and no critical flags
    critical_flags = {"NO_SOURCES_AVAILABLE", "INSUFFICIENT_SOURCES"}
    passed = overall_score >= 0.5 and not any(flag in critical_flags for flag in flags)

    return QualityReport(
        passed=passed,
        score=overall_score,
        flags=flags,
    )
