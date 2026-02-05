"""Schema validation tests for ingestion models."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from ingestion.schema import (
    IngestedMatchData,
    MatchIdentity,
    MatchState,
    OddsSnapshot,
)


def test_match_identity_validation():
    """MatchIdentity accepts valid fields and validates types."""
    m = MatchIdentity(
        match_id="m1",
        home_team="Home",
        away_team="Away",
        competition="League",
        kickoff_utc=datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
    )
    assert m.match_id == "m1"
    assert m.home_team == "Home"
    assert m.away_team == "Away"
    assert m.competition == "League"


def test_odds_snapshot_validation():
    """OddsSnapshot requires positive odds and valid datetime."""
    o = OddsSnapshot(
        market="1X2",
        selection="HOME",
        odds=2.5,
        source="test",
        collected_at_utc=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert o.market == "1X2"
    assert o.odds == 2.5
    assert o.source == "test"


def test_odds_snapshot_rejects_non_positive_odds():
    """OddsSnapshot rejects odds <= 0."""
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        OddsSnapshot(
            market="1X2",
            selection="HOME",
            odds=0.0,
            source="test",
            collected_at_utc=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )


def test_match_state_validation():
    """MatchState accepts optional minute/score and status."""
    s = MatchState(minute=45, score_home=1, score_away=0, status="LIVE")
    assert s.minute == 45
    assert s.score_home == 1
    assert s.score_away == 0
    assert s.status == "LIVE"

    s2 = MatchState(minute=None, score_home=None, score_away=None, status="SCHEDULED")
    assert s2.minute is None
    assert s2.status == "SCHEDULED"


def test_ingested_match_data_validation():
    """IngestedMatchData requires identity, allows empty odds and optional state."""
    identity = MatchIdentity(
        match_id="m1",
        home_team="H",
        away_team="A",
        competition="C",
        kickoff_utc=datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
    )
    data = IngestedMatchData(identity=identity, odds=[], state=None)
    assert data.identity.match_id == "m1"
    assert data.odds == []
    assert data.state is None

    state = MatchState(minute=None, score_home=None, score_away=None, status="SCHEDULED")
    data2 = IngestedMatchData(identity=identity, odds=[], state=state)
    assert data2.state is not None
    assert data2.state.status == "SCHEDULED"
