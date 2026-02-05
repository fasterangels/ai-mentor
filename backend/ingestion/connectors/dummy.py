"""
Dummy connector for tests only: hardcoded deterministic data.

No network calls. Fully conforms to schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ingestion.schema import (
    IngestedMatchData,
    MatchIdentity,
    MatchState,
    OddsSnapshot,
)
from .base import DataConnector

# Deterministic fake data (tests only)
_DUMMY_KICKOFF = datetime(2025, 6, 1, 18, 0, 0, tzinfo=timezone.utc)
_DUMMY_COLLECTED = datetime(2025, 5, 31, 12, 0, 0, tzinfo=timezone.utc)

_MATCHES: List[MatchIdentity] = [
    MatchIdentity(
        match_id="dummy-match-1",
        home_team="Team A",
        away_team="Team B",
        competition="Test League",
        kickoff_utc=_DUMMY_KICKOFF,
    ),
    MatchIdentity(
        match_id="dummy-match-2",
        home_team="Team C",
        away_team="Team D",
        competition="Test League",
        kickoff_utc=_DUMMY_KICKOFF.replace(hour=20, minute=0),
    ),
]

_ODDS_1: List[OddsSnapshot] = [
    OddsSnapshot(
        market="1X2",
        selection="HOME",
        odds=2.10,
        source="dummy",
        collected_at_utc=_DUMMY_COLLECTED,
    ),
    OddsSnapshot(
        market="1X2",
        selection="DRAW",
        odds=3.40,
        source="dummy",
        collected_at_utc=_DUMMY_COLLECTED,
    ),
    OddsSnapshot(
        market="1X2",
        selection="AWAY",
        odds=3.20,
        source="dummy",
        collected_at_utc=_DUMMY_COLLECTED,
    ),
]

_STATE_SCHEDULED = MatchState(minute=None, score_home=None, score_away=None, status="SCHEDULED")


class DummyConnector(DataConnector):
    """Test-only connector with hardcoded matches and odds."""

    def fetch_matches(self) -> List[MatchIdentity]:
        return list(_MATCHES)

    def fetch_match_data(self, match_id: str) -> IngestedMatchData:
        if match_id == "dummy-match-1":
            identity = _MATCHES[0]
            return IngestedMatchData(
                identity=identity,
                odds=_ODDS_1,
                state=_STATE_SCHEDULED,
            )
        if match_id == "dummy-match-2":
            identity = _MATCHES[1]
            return IngestedMatchData(
                identity=identity,
                odds=[],
                state=_STATE_SCHEDULED,
            )
        raise KeyError(f"Unknown match_id: {match_id}")
