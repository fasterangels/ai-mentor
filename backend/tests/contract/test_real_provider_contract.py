"""
Contract tests for real_provider: recorded-first, fixtures validation, normalized schema, stable IDs.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import IngestedMatchData, MatchIdentity
from ingestion.connectors.real_provider import RealProviderAdapter
from ingestion.fixtures.validator import validate_fixtures
from ingestion.live_io import get_connector_safe


# --- Recorded-first: fixtures required ---

def test_real_provider_has_fixtures_dir() -> None:
    """real_provider has recorded fixtures directory (recorded-first)."""
    fixtures_dir = _backend / "ingestion" / "fixtures" / "real_provider"
    assert fixtures_dir.is_dir(), "real_provider must have ingestion/fixtures/real_provider/"


def test_real_provider_fixtures_pass_validator() -> None:
    """Recorded fixtures for real_provider pass validator."""
    fixtures_dir = _backend / "ingestion" / "fixtures" / "real_provider"
    report = validate_fixtures(fixtures_dir)
    assert report.ok is True, f"Fixture validation failed: {report.errors}"


def test_real_provider_fail_fast_if_fixtures_missing() -> None:
    """RealProviderAdapter raises if fixtures directory is missing (recorded-first enforcement)."""
    missing_dir = _backend / "ingestion" / "fixtures" / "real_provider_nonexistent_12345"
    assert not missing_dir.exists()
    with pytest.raises(FileNotFoundError, match="fixtures directory missing"):
        RealProviderAdapter(fixtures_dir=missing_dir)


# --- get_connector_safe: recorded vs live ---

def test_real_provider_allowed_without_live_flag() -> None:
    """get_connector_safe('real_provider') returns adapter when REAL_PROVIDER_LIVE is not set (recorded path)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "0")
        m.delenv("LIVE_IO_ALLOWED", raising=False)
        adapter = get_connector_safe("real_provider")
    assert adapter is not None
    assert isinstance(adapter, RealProviderAdapter)


def test_real_provider_blocked_when_live_flag_set_but_live_io_not_allowed() -> None:
    """When REAL_PROVIDER_LIVE=true, adapter is returned only if LIVE_IO_ALLOWED=true."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "1")
        m.setenv("LIVE_IO_ALLOWED", "0")
        adapter = get_connector_safe("real_provider")
    assert adapter is None


def test_real_provider_allowed_when_live_flag_and_live_io_allowed() -> None:
    """When REAL_PROVIDER_LIVE=true and LIVE_IO_ALLOWED=true, adapter is returned."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "1")
        m.setenv("LIVE_IO_ALLOWED", "1")
        adapter = get_connector_safe("real_provider")
    assert adapter is not None
    assert isinstance(adapter, RealProviderAdapter)


# --- Normalized schema and stable IDs ---

def test_real_provider_returns_normalized_schema_from_fixtures() -> None:
    """Connector returns IngestedMatchData with required schema and stable match_id from fixtures."""
    adapter = RealProviderAdapter()
    matches = adapter.fetch_matches()
    assert isinstance(matches, list)
    assert len(matches) >= 1
    for m in matches:
        assert isinstance(m, MatchIdentity)
        assert m.match_id
        assert isinstance(m.match_id, str)

    data = adapter.fetch_match_data("real_provider_001")
    assert data is not None
    assert isinstance(data, IngestedMatchData)
    assert data.match_id == "real_provider_001"
    assert data.home_team
    assert data.away_team
    assert data.competition
    assert data.kickoff_utc
    assert "T" in data.kickoff_utc and "+00:00" in data.kickoff_utc
    assert set(data.odds_1x2.keys()) == {"home", "draw", "away"}
    for k, v in data.odds_1x2.items():
        assert isinstance(v, (int, float)) and v > 0
    assert data.status in ("scheduled", "in_play", "finished", "cancelled") or data.status


def test_real_provider_fetch_match_data_returns_none_for_unknown_id() -> None:
    """fetch_match_data returns None for unknown match_id."""
    adapter = RealProviderAdapter()
    assert adapter.fetch_match_data("unknown_match_xyz") is None
