"""
Tests for sample platform adapter: load fixtures, fetch_matches, fetch_match_data, ValueError on missing fields.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import IngestedMatchData, MatchIdentity
from ingestion.connectors.sample_platform import SamplePlatformAdapter


def test_adapter_loads_fixtures() -> None:
    """Adapter load_fixtures returns at least the sample fixture records."""
    adapter = SamplePlatformAdapter()
    fixtures = adapter.load_fixtures()
    assert isinstance(fixtures, list)
    assert len(fixtures) >= 2
    for f in fixtures:
        assert isinstance(f, dict)
        assert "match_id" in f or "id" in f
        assert "home_team" in f and "away_team" in f


def test_fetch_matches_returns_deterministic_identities() -> None:
    """fetch_matches returns list of MatchIdentity in deterministic order."""
    adapter = SamplePlatformAdapter()
    identities = adapter.fetch_matches()
    assert isinstance(identities, list)
    assert len(identities) >= 2
    for ident in identities:
        assert isinstance(ident, MatchIdentity)
        assert ident.match_id
    match_ids = [i.match_id for i in identities]
    assert match_ids == sorted(match_ids)


def test_fetch_match_data_returns_valid_ingested_match_data() -> None:
    """fetch_match_data returns valid IngestedMatchData for a fixture match_id."""
    adapter = SamplePlatformAdapter()
    # Use match_id from our fixture files
    data = adapter.fetch_match_data("sample_platform_match_001")
    assert data is not None
    assert isinstance(data, IngestedMatchData)
    assert data.match_id == "sample_platform_match_001"
    assert data.home_team == "North FC"
    assert data.away_team == "South United"
    assert data.competition == "Sample League"
    assert "T19:00:00" in data.kickoff_utc or "19:00:00" in data.kickoff_utc
    assert data.odds_1x2["home"] == 2.10
    assert data.odds_1x2["draw"] == 3.40
    assert data.odds_1x2["away"] == 3.20
    assert data.status == "scheduled"


def test_fetch_match_data_unknown_id_returns_none() -> None:
    """fetch_match_data returns None for unknown match_id."""
    adapter = SamplePlatformAdapter()
    assert adapter.fetch_match_data("nonexistent_match_999") is None


def test_parse_fixture_missing_required_raises_value_error() -> None:
    """parse_fixture raises ValueError when required field is missing."""
    adapter = SamplePlatformAdapter()
    with pytest.raises(ValueError) as exc_info:
        adapter.parse_fixture({})
    assert "required" in str(exc_info.value).lower()

    with pytest.raises(ValueError):
        adapter.parse_fixture({"match_id": "x", "home_team": "A", "away_team": "B"})  # missing competition, etc.

    with pytest.raises(ValueError):
        adapter.parse_fixture({
            "match_id": "x",
            "home_team": "A",
            "away_team": "B",
            "competition": "C",
            "kickoff_utc": "2025-01-01T12:00:00Z",
            "status": "scheduled",
        })  # missing odds_1x2


def test_parse_fixture_invalid_odds_raises_value_error() -> None:
    """parse_fixture raises ValueError when odds_1x2 is invalid."""
    adapter = SamplePlatformAdapter()
    base = {
        "match_id": "x",
        "home_team": "A",
        "away_team": "B",
        "competition": "C",
        "kickoff_utc": "2025-01-01T12:00:00Z",
        "status": "scheduled",
    }
    with pytest.raises(ValueError):
        adapter.parse_fixture({**base, "odds_1x2": {"home": 2.0}})  # missing draw, away
    with pytest.raises(ValueError):
        adapter.parse_fixture({**base, "odds_1x2": {"home": "x", "draw": 3.0, "away": 4.0}})  # non-numeric
