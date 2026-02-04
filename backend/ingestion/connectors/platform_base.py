"""
Platform adapter contract for recorded (fixture-only) ingestion.
No HTTP requests; all data from local fixture files.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class MatchIdentity:
    """Minimal identity for a match from a connector."""

    match_id: str
    kickoff_utc: str | None = None  # ISO8601
    competition: str | None = None


@dataclass
class IngestedMatchData:
    """Parsed match data from a platform fixture (ready for pipeline consumption)."""

    match_id: str
    home_team: str
    away_team: str
    competition: str
    kickoff_utc: str  # ISO8601 normalized to UTC
    odds_1x2: Dict[str, float]  # "home", "draw", "away" -> decimal odds
    status: str  # e.g. "scheduled", "in_play", "finished"


class DataConnector(ABC):
    """Abstract connector: provides match list and match data."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def fetch_matches(self) -> List[MatchIdentity]:
        raise NotImplementedError

    @abstractmethod
    def fetch_match_data(self, match_id: str) -> IngestedMatchData | None:
        raise NotImplementedError


class RecordedPlatformAdapter(DataConnector):
    """
    Adapter that MUST NOT perform HTTP requests.
    All data from local fixture files via load_fixtures() and parse_fixture().
    """

    @property
    def name(self) -> str:
        return "recorded"

    def load_fixtures(self) -> List[Dict[str, Any]]:
        """Load all fixture records from local storage (e.g. JSON files)."""
        raise NotImplementedError

    def parse_fixture(self, raw: Dict[str, Any]) -> IngestedMatchData:
        """
        Parse one raw fixture dict into IngestedMatchData.
        If a required field is missing, raise ValueError with a clear message.
        """
        raise NotImplementedError

    def fetch_matches(self) -> List[MatchIdentity]:
        fixtures = self.load_fixtures()
        identities: List[MatchIdentity] = []
        for raw in fixtures:
            try:
                parsed = self.parse_fixture(raw)
                identities.append(MatchIdentity(
                    match_id=parsed.match_id,
                    kickoff_utc=parsed.kickoff_utc,
                    competition=parsed.competition,
                ))
            except ValueError:
                continue
        return identities

    def fetch_match_data(self, match_id: str) -> IngestedMatchData | None:
        for raw in self.load_fixtures():
            rid = raw.get("match_id") or raw.get("id")
            if str(rid) == str(match_id):
                return self.parse_fixture(raw)
        return None
