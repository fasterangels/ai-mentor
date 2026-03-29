"""
Normalized input schema for recorded evidence items (JSON file format).
Validate required fields and map to domain EvidenceItem.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from domain.evidence.canonicalization import evidence_checksum
from domain.evidence.types import (
    EvidenceItem,
    EvidenceType,
    ReliabilityTier,
    SourceClass,
)

REQUIRED_KEYS = {"fixture_id", "items"}
ITEM_REQUIRED = {"title", "evidence_type", "source_class", "source_name", "reliability_tier", "observed_at"}


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _parse_evidence_type(v: Any) -> EvidenceType:
    if isinstance(v, EvidenceType):
        return v
    s = (v or "").strip().upper()
    for t in EvidenceType:
        if t.value == s:
            return t
    raise ValueError(f"evidence_type must be one of {[e.value for e in EvidenceType]}, got {v!r}")


def _parse_source_class(v: Any) -> SourceClass:
    if isinstance(v, SourceClass):
        return v
    s = (v or "").strip().upper()
    for c in SourceClass:
        if c.value == s:
            return c
    raise ValueError(f"source_class must be one of {[c.value for c in SourceClass]}, got {v!r}")


def _parse_reliability_tier(v: Any) -> ReliabilityTier:
    if isinstance(v, ReliabilityTier):
        return v
    s = (v or "").strip().upper()
    for t in ReliabilityTier:
        if t.value == s:
            return t
    raise ValueError(f"reliability_tier must be one of {[t.value for t in ReliabilityTier]}, got {v!r}")


def parse_recorded_evidence_item(
    raw: Dict[str, Any],
    fixture_id: str,
    evidence_id: str,
    created_at: datetime,
) -> EvidenceItem:
    """
    Parse one raw item from recorded JSON into EvidenceItem.
    Raises ValueError if required fields are missing or invalid.
    """
    for k in ITEM_REQUIRED:
        if k not in raw:
            raise ValueError(f"evidence item missing required key: {k!r}")

    observed_at = _parse_dt(raw["observed_at"])
    if not observed_at:
        raise ValueError("observed_at must be ISO8601 datetime")

    effective_from = _parse_dt(raw.get("effective_from")) or observed_at
    expected_valid_until = _parse_dt(raw.get("expected_valid_until"))
    title = str((raw.get("title") or "").strip())[:256]
    if not title:
        raise ValueError("title must be non-empty")

    description = raw.get("description")
    if description is not None:
        description = str(description)[:2000]

    evidence_type = _parse_evidence_type(raw["evidence_type"])
    source_class = _parse_source_class(raw["source_class"])
    source_name = str((raw.get("source_name") or "").strip())
    if not source_name:
        raise ValueError("source_name must be non-empty")
    source_ref = str(raw["source_ref"]).strip() if raw.get("source_ref") is not None else None
    reliability_tier = _parse_reliability_tier(raw["reliability_tier"])

    team_id = str(raw["team_id"]).strip() if raw.get("team_id") is not None else None
    player_id = str(raw["player_id"]).strip() if raw.get("player_id") is not None else None
    conflict_group_id = str(raw["conflict_group_id"]).strip() if raw.get("conflict_group_id") is not None else None
    tags_raw = raw.get("tags")
    tags: Optional[List[str]] = None
    if isinstance(tags_raw, list):
        tags = [str(x).strip() for x in tags_raw if x is not None][:50]

    item = EvidenceItem(
        evidence_id=evidence_id,
        fixture_id=fixture_id,
        team_id=team_id,
        player_id=player_id,
        evidence_type=evidence_type,
        title=title,
        description=description,
        source_class=source_class,
        source_name=source_name,
        source_ref=source_ref,
        reliability_tier=reliability_tier,
        observed_at=observed_at,
        effective_from=effective_from,
        expected_valid_until=expected_valid_until,
        created_at=created_at,
        checksum="",
        conflict_group_id=conflict_group_id,
        tags=tags,
    )
    item.checksum = evidence_checksum(item)
    return item


def parse_recorded_evidence_payload(
    payload: Dict[str, Any],
    created_at: Optional[datetime] = None,
) -> List[EvidenceItem]:
    """
    Parse a recorded evidence payload: { "fixture_id": "...", "items": [ ... ] }.
    Returns list of EvidenceItem with checksums set. Raises ValueError if invalid.
    """
    for k in REQUIRED_KEYS:
        if k not in payload:
            raise ValueError(f"recorded evidence payload missing required key: {k!r}")

    fixture_id = str(payload["fixture_id"]).strip()
    if not fixture_id:
        raise ValueError("fixture_id must be non-empty")

    items_raw = payload.get("items")
    if not isinstance(items_raw, list):
        raise ValueError("items must be an array")

    now = created_at or datetime.now(timezone.utc)
    result: List[EvidenceItem] = []
    for i, raw in enumerate(items_raw):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{i}] must be an object")
        evidence_id = str(uuid.uuid4())
        result.append(parse_recorded_evidence_item(raw, fixture_id, evidence_id, now))
    return result
