"""
Tests for sample_recorded_platform_v2 adapter: contract + recorded-only behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import IngestedMatchData
from ingestion.connectors.sample_recorded_platform_v2 import SampleRecordedPlatformV2Adapter
from tests.contract.test_platform_adapter_contract import assert_adapter_contract


def test_sample_recorded_platform_v2_adapter_contract() -> None:
    """Mandatory contract tests for sample_recorded_platform_v2 adapter."""
    assert_adapter_contract("sample_recorded_platform_v2", "ingestion/fixtures/sample_recorded_platform_v2")


def test_fetch_match_data_unknown_id_returns_none() -> None:
    """fetch_match_data returns None for unknown match_id."""
    adapter = SampleRecordedPlatformV2Adapter()
    assert adapter.fetch_match_data("nonexistent_match_999") is None


def test_load_fixtures_returns_recorded_data_only() -> None:
    """load_fixtures returns list of dicts from local JSON; no live IO."""
    adapter = SampleRecordedPlatformV2Adapter()
    fixtures = adapter.load_fixtures()
    assert len(fixtures) >= 2
    for f in fixtures:
        assert isinstance(f, dict)
        assert "match_id" in f
        assert "home_team" in f and "away_team" in f


def test_parse_fixture_invalid_odds_raises_value_error() -> None:
    """parse_fixture raises ValueError when odds_1x2 is invalid."""
    adapter = SampleRecordedPlatformV2Adapter()
    base = {
        "match_id": "x",
        "home_team": "A",
        "away_team": "B",
        "competition": "C",
        "kickoff_utc": "2025-01-01T12:00:00Z",
        "status": "scheduled",
    }
    with pytest.raises(ValueError):
        adapter.parse_fixture({**base, "odds_1x2": {"home": 2.0}})
    with pytest.raises(ValueError):
        adapter.parse_fixture({**base, "odds_1x2": {"home": "x", "draw": 3.0, "away": 4.0}})
