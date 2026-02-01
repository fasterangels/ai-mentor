from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .types import DomainData, QualityReport


def _parse_datetime(iso_str: str) -> datetime:
    """Parse ISO datetime string to timezone-aware datetime."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _merge_field(
    field_name: str,
    payloads: List[Dict[str, Any]],
    tolerance: float = 0.0,
) -> tuple[Any, bool]:
    """Merge a field from multiple payloads deterministically.

    Prefers:
    1. Higher source_confidence
    2. Fresher fetched_at_utc

    Returns:
        Tuple of (merged_value, has_disagreement)
    """
    if not payloads:
        return None, False

    # Sort by confidence (desc) then freshness (desc)
    sorted_payloads = sorted(
        payloads,
        key=lambda p: (
            p.get("source_confidence", 0.0),
            _parse_datetime(p.get("fetched_at_utc", "")).timestamp(),
        ),
        reverse=True,
    )

    # Get values from all payloads
    values = []
    for payload in sorted_payloads:
        data = payload.get("data", {})
        if field_name in data:
            values.append(data[field_name])

    if not values:
        return None, False

    # Use highest-confidence value
    merged_value = values[0]

    # Check for disagreement (if numeric, check tolerance)
    if len(values) > 1:
        if isinstance(merged_value, (int, float)):
            disagreement = any(
                abs(v - merged_value) > tolerance
                for v in values[1:]
                if isinstance(v, (int, float))
            )
        else:
            # For non-numeric, any difference is disagreement
            disagreement = any(v != merged_value for v in values[1:])
    else:
        disagreement = False

    return merged_value, disagreement


def build_consensus(
    payloads: List[Dict[str, Any]],
    quality_report: QualityReport,
    domain: str,
) -> DomainData:
    """Build consensus from multiple normalized payloads.

    Args:
        payloads: List of normalized payload dicts
        quality_report: Quality assessment for these payloads
        domain: Domain name (e.g., "fixtures", "stats")

    Returns:
        DomainData with merged data, quality, and source list
    """
    if not payloads:
        return DomainData(
            data={},
            quality=quality_report,
            sources=[],
        )

    # Collect source names
    sources = [p.get("source_name", "unknown") for p in payloads]

    # Determine fields to merge based on domain
    # TODO: Make field mapping configurable per domain
    if domain == "fixtures":
        fields_to_merge = [
            "match_id",
            "home_team",
            "away_team",
            "kickoff_utc",
            "venue",
            "competition",
            "status",
        ]
    elif domain == "stats":
        fields_to_merge = [
            "match_id",
            "home_team_stats",
            "away_team_stats",
            "head_to_head",
        ]
    else:
        # Generic: merge all top-level fields from first payload
        first_data = payloads[0].get("data", {})
        fields_to_merge = list(first_data.keys())

    # Merge fields deterministically
    merged_data: Dict[str, Any] = {}
    has_disagreement = False

    for field_name in fields_to_merge:
        value, disagreement = _merge_field(field_name, payloads, tolerance=0.1)
        if value is not None:
            merged_data[field_name] = value
        if disagreement:
            has_disagreement = True

    # Add disagreement flag if detected
    flags = list(quality_report.flags)
    if has_disagreement:
        flags.append("LOW_AGREEMENT")

    updated_quality = QualityReport(
        passed=quality_report.passed,
        score=quality_report.score,
        flags=flags,
    )

    return DomainData(
        data=merged_data,
        quality=updated_quality,
        sources=sources,
    )
