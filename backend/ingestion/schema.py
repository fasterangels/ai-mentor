"""
Normalized, source-agnostic ingestion schema for match and odds data.

Deterministic and platform-independent. Used by data connectors.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MatchIdentity(BaseModel):
    """Canonical identity of a match (source-agnostic)."""

    match_id: str = Field(..., description="Unique match identifier")
    home_team: str = Field(..., description="Home team name or id")
    away_team: str = Field(..., description="Away team name or id")
    competition: str = Field(..., description="Competition/league name or id")
    kickoff_utc: datetime = Field(..., description="Scheduled kickoff in UTC")


class OddsSnapshot(BaseModel):
    """Single odds quote for a market selection at a point in time."""

    market: str = Field(..., description="Market type (e.g. 1X2, OVER_UNDER_25)")
    selection: str = Field(..., description="Selection (e.g. HOME, OVER)")
    odds: float = Field(..., gt=0, description="Decimal odds")
    source: str = Field(..., description="Source identifier")
    collected_at_utc: datetime = Field(..., description="When the quote was collected (UTC)")
    checksum: Optional[str] = Field(None, description="SHA-256 of stable fields (set by ingestion)")


class MatchState(BaseModel):
    """Live or final match state (minute, score, status)."""

    minute: Optional[int] = Field(None, ge=0, le=150, description="Match minute (null if not started)")
    score_home: Optional[int] = Field(None, ge=0, description="Home team goals")
    score_away: Optional[int] = Field(None, ge=0, description="Away team goals")
    status: str = Field(..., description="e.g. SCHEDULED, LIVE, FINAL, POSTPONED")


class IngestedMatchData(BaseModel):
    """Full normalized payload for one match: identity, odds snapshots, optional state, and provenance."""

    identity: MatchIdentity = Field(..., description="Match identity")
    odds: List[OddsSnapshot] = Field(default_factory=list, description="Odds snapshots")
    state: Optional[MatchState] = Field(None, description="Current or final match state (optional)")
    source: Optional[str] = Field(None, description="Connector name (set by ingestion)")
    collected_at_utc: Optional[datetime] = Field(None, description="When payload was collected (UTC)")
    checksum: Optional[str] = Field(None, description="SHA-256 of identity + odds checksums + state")
