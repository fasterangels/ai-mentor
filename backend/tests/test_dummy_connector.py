"""Dummy connector returns valid IngestedMatchData."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from ingestion.schema import IngestedMatchData, MatchIdentity
from ingestion.connectors.dummy import DummyConnector


def test_dummy_fetch_matches_returns_list_of_match_identity():
    """Dummy connector fetch_matches returns valid MatchIdentity list."""
    connector = DummyConnector()
    matches = connector.fetch_matches()
    assert len(matches) >= 1
    assert all(isinstance(m, MatchIdentity) for m in matches)
    ids = [m.match_id for m in matches]
    assert "dummy-match-1" in ids


def test_dummy_fetch_match_data_returns_ingested_match_data():
    """Dummy connector fetch_match_data returns valid IngestedMatchData for known match."""
    connector = DummyConnector()
    data = connector.fetch_match_data("dummy-match-1")
    assert isinstance(data, IngestedMatchData)
    assert data.identity.match_id == "dummy-match-1"
    assert data.identity.home_team == "Team A"
    assert data.identity.away_team == "Team B"
    assert data.identity.competition == "Test League"
    assert len(data.odds) >= 1
    assert data.state is not None
    assert data.state.status == "SCHEDULED"


def test_dummy_fetch_match_data_second_match():
    """Dummy connector returns valid data for second match (empty odds)."""
    connector = DummyConnector()
    data = connector.fetch_match_data("dummy-match-2")
    assert isinstance(data, IngestedMatchData)
    assert data.identity.match_id == "dummy-match-2"
    assert data.identity.home_team == "Team C"
    assert data.odds == []
    assert data.state is not None


def test_dummy_fetch_match_data_unknown_raises():
    """Dummy connector fetch_match_data raises for unknown match_id."""
    import pytest
    connector = DummyConnector()
    with pytest.raises(KeyError, match="Unknown match_id"):
        connector.fetch_match_data("unknown-id")
