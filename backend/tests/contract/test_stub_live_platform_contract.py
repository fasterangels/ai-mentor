"""
Contract tests for stub_live_platform: recorded-first, LIVE_IO_ALLOWED and LIVE_WRITES_ALLOWED gates,
stub connector normalization shape. Fixtures validator pass for recorded-first.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

from ingestion.connectors.platform_base import IngestedMatchData, MatchIdentity
from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
from ingestion.fixtures.validator import validate_fixtures
from ingestion.live_io import get_connector_safe, live_io_allowed, live_writes_allowed
from dev.stub_server import create_stub_app


# --- Recorded-first: fixtures required ---

def test_stub_live_platform_has_fixtures_dir() -> None:
    """stub_live_platform has recorded fixtures directory (recorded-first)."""
    fixtures_dir = _backend / "ingestion" / "fixtures" / "stub_live_platform"
    assert fixtures_dir.is_dir(), "stub_live_platform must have ingestion/fixtures/stub_live_platform/"


def test_stub_live_platform_fixtures_pass_validator() -> None:
    """Recorded fixtures for stub_live_platform pass validator (reuse existing validator)."""
    fixtures_dir = _backend / "ingestion" / "fixtures" / "stub_live_platform"
    report = validate_fixtures(fixtures_dir)
    assert report.ok is True, f"Fixture validation failed: {report.errors}"


# --- LIVE_IO_ALLOWED gate ---

def test_stub_live_platform_blocked_without_live_io_allowed() -> None:
    """get_connector_safe('stub_live_platform') returns None when LIVE_IO_ALLOWED is false."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        adapter = get_connector_safe("stub_live_platform")
    assert adapter is None


def test_stub_live_platform_allowed_when_live_io_enabled() -> None:
    """get_connector_safe('stub_live_platform') returns adapter when LIVE_IO_ALLOWED=true."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        adapter = get_connector_safe("stub_live_platform")
    assert adapter is not None
    assert isinstance(adapter, StubLivePlatformAdapter)


def test_stub_live_platform_fails_fast_when_called_without_live_io() -> None:
    """Connector raises when fetch_matches/fetch_match_data called without LIVE_IO_ALLOWED (fail fast)."""
    from ingestion.registry import get_connector
    adapter = get_connector("stub_live_platform")
    assert adapter is not None
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        with pytest.raises(RuntimeError, match="LIVE_IO_ALLOWED"):
            adapter.fetch_matches()
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        with pytest.raises(RuntimeError, match="LIVE_IO_ALLOWED"):
            adapter.fetch_match_data("stub_live_001")


# --- LIVE_WRITES_ALLOWED gate ---

def test_live_writes_allowed_default_false() -> None:
    """live_writes_allowed() defaults to False (read-only default)."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("LIVE_WRITES_ALLOWED", raising=False)
        assert live_writes_allowed() is False


# --- Stub connector normalization shape ---

def test_stub_live_platform_normalization_shape_via_stub() -> None:
    """Stub connector returns IngestedMatchData with required schema (via local stub, no external IO)."""
    app = create_stub_app()
    client = TestClient(app)
    adapter = StubLivePlatformAdapter()
    # Point adapter at test client (no real network)
    def patched_get(path: str):
        r = client.get(path)
        r.raise_for_status()
        return r.json()
    adapter._get = patched_get
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        data = adapter.fetch_match_data("stub_live_001")
    assert data is not None
    assert isinstance(data, IngestedMatchData)
    assert data.match_id == "stub_live_001"
    assert data.home_team == "Alpha FC"
    assert data.away_team == "Beta United"
    assert data.competition == "Stub Live League"
    assert "T" in data.kickoff_utc or "Z" in data.kickoff_utc or "+" in data.kickoff_utc
    assert set(data.odds_1x2.keys()) >= {"home", "draw", "away"}
    assert all(v > 0 for v in data.odds_1x2.values())
    assert data.status in ("scheduled", "in_play", "finished", "FINAL")
    adapter.close()


def test_stub_live_platform_fetch_matches_shape() -> None:
    """fetch_matches returns sorted list of MatchIdentity."""
    app = create_stub_app()
    client = TestClient(app)
    adapter = StubLivePlatformAdapter()
    def patched_get(path: str):
        r = client.get(path)
        r.raise_for_status()
        return r.json()
    adapter._get = patched_get
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        matches = adapter.fetch_matches()
    assert isinstance(matches, list)
    assert len(matches) >= 2
    for m in matches:
        assert isinstance(m, MatchIdentity)
        assert m.match_id
    ids = [m.match_id for m in matches]
    assert ids == sorted(ids)
    adapter.close()
