"""
Evidence schema v1: enums and EvidenceItem type.
Used for injuries, suspensions, team news, external disruptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class EvidenceType(str, Enum):
    """Type of time-sensitive evidence."""

    INJURY = "INJURY"
    SUSPENSION = "SUSPENSION"
    TEAM_NEWS = "TEAM_NEWS"
    DISRUPTION = "DISRUPTION"


class SourceClass(str, Enum):
    """Provenance: where the evidence came from."""

    RECORDED = "RECORDED"
    LIVE_SHADOW = "LIVE_SHADOW"
    EDITORIAL = "EDITORIAL"
    UNKNOWN = "UNKNOWN"


class ReliabilityTier(str, Enum):
    """Reliability tier for the source (A=highest, C=lowest)."""

    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


# Bounded lengths for storage
TITLE_MAX_LEN = 256
DESCRIPTION_MAX_LEN = 2000


@dataclass(frozen=False)
class EvidenceItem:
    """
    Single evidence item for a fixture: injury, suspension, team news, or disruption.
    All timestamps are timezone-aware (UTC). Same canonical content -> same checksum.
    """

    evidence_id: str
    fixture_id: str
    team_id: Optional[str]
    player_id: Optional[str]
    evidence_type: EvidenceType
    title: str
    description: Optional[str]
    source_class: SourceClass
    source_name: str
    source_ref: Optional[str]
    reliability_tier: ReliabilityTier
    observed_at: datetime
    effective_from: Optional[datetime]
    expected_valid_until: Optional[datetime]
    created_at: datetime
    checksum: str
    conflict_group_id: Optional[str]
    tags: Optional[List[str]]

    def __post_init__(self) -> None:
        if self.title and len(self.title) > TITLE_MAX_LEN:
            object.__setattr__(self, "title", self.title[:TITLE_MAX_LEN])
        if self.description and len(self.description) > DESCRIPTION_MAX_LEN:
            object.__setattr__(self, "description", self.description[:DESCRIPTION_MAX_LEN])
