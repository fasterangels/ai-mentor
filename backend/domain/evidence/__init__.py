"""
Evidence schema v1: injuries, suspensions, team news, disruptions.
Offline-first, deterministic; no decision logic integration.
"""

from domain.evidence.types import (
    EvidenceItem,
    EvidenceType,
    ReliabilityTier,
    SourceClass,
)
from domain.evidence.canonicalization import evidence_checksum

__all__ = [
    "EvidenceItem",
    "EvidenceType",
    "ReliabilityTier",
    "SourceClass",
    "evidence_checksum",
]
