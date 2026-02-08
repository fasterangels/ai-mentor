"""
Deterministic checksum for evidence items: stable JSON (sorted keys) + SHA-256.
Same content -> same checksum; used for deduping and audit.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from domain.evidence.types import EvidenceItem, EvidenceType, ReliabilityTier, SourceClass


def _evidence_to_canonical_dict(item: EvidenceItem) -> Dict[str, Any]:
    """Build a dict of fields that contribute to content identity (sorted keys for stability)."""
    effective_from = item.effective_from.isoformat() if item.effective_from else None
    expected_valid_until = item.expected_valid_until.isoformat() if item.expected_valid_until else None
    observed_at = item.observed_at.isoformat() if item.observed_at else None
    created_at = item.created_at.isoformat() if item.created_at else None
    return {
        "conflict_group_id": item.conflict_group_id,
        "description": item.description,
        "effective_from": effective_from,
        "evidence_type": item.evidence_type.value if isinstance(item.evidence_type, EvidenceType) else item.evidence_type,
        "expected_valid_until": expected_valid_until,
        "fixture_id": item.fixture_id,
        "observed_at": observed_at,
        "player_id": item.player_id,
        "reliability_tier": item.reliability_tier.value if isinstance(item.reliability_tier, ReliabilityTier) else item.reliability_tier,
        "source_class": item.source_class.value if isinstance(item.source_class, SourceClass) else item.source_class,
        "source_name": item.source_name,
        "source_ref": item.source_ref,
        "team_id": item.team_id,
        "title": item.title,
        "tags": sorted(item.tags) if item.tags else None,
        "created_at": created_at,
    }


def evidence_checksum(item: EvidenceItem) -> str:
    """
    Return SHA-256 hex digest of canonicalized evidence content.
    Same content (including field order normalized via sorted keys) -> same checksum.
    """
    canonical = _evidence_to_canonical_dict(item)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
