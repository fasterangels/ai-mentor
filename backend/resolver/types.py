from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class MatchResolutionInput:
    """Input for match resolution."""

    home_text: str
    away_text: str
    kickoff_hint_utc: Optional[datetime] = None
    window_hours: int = 24
    competition_id: Optional[str] = None


@dataclass
class MatchCandidate:
    """A candidate match in resolution results."""

    match_id: str
    kickoff_utc: datetime
    competition_id: str


@dataclass
class MatchResolutionOutput:
    """Output from match resolution."""

    status: str  # "RESOLVED" | "AMBIGUOUS" | "NOT_FOUND"
    match_id: Optional[str] = None
    candidates: List[MatchCandidate] = None
    notes: List[str] = None

    def __post_init__(self) -> None:
        """Initialize default values for lists."""
        if self.candidates is None:
            self.candidates = []
        if self.notes is None:
            self.notes = []
