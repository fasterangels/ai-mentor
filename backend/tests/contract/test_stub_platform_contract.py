"""
Contract tests for stub platform: stub server and stub connector.
Tests live IO connector that fetches from local HTTP stub server.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

from ingestion.connectors.platform_base import IngestedMatchData, MatchIdentity
from ingestion.connectors.stub_platform import StubPlatformAdapter
from ingestion.live_io import execution_mode_context, get_connector_safe
from ingestion.stub_server import create_stub_app


@pytest.fixture
def stub_app():
    """Create stub app for testing."""
    return create_stub_app()


@pytest.fixture
def stub_client(stub_app):
    """Create test client for stub app."""
    return TestClient(stub_app)


def test_stub_server_health_endpoint(stub_client):
    """Stub server health endpoint returns OK."""
    response = stub_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "fixtures_count" in data
    assert data["fixtures_count"] >= 0


def test_stub_server_list_matches(stub_client):
    """Stub server /matches returns list of fixtures."""
    response = stub_client.get("/matches")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # match_001 and match_002
    for match in data:
        assert "match_id" in match or "id" in match
        assert "home_team" in match
        assert "away_team" in match


def test_stub_server_get_match_by_id(stub_client):
    """Stub server /matches/{match_id} returns specific match."""
    response = stub_client.get("/matches/stub_platform_match_001")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "stub_platform_match_001"
    assert data["home_team"] == "North FC"
    assert "odds_1x2" in data


def test_stub_server_get_match_not_found(stub_client):
    """Stub server returns 404 for unknown match_id."""
    response = stub_client.get("/matches/unknown_match_xyz")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_stub_connector_fetch_matches():
    """Stub connector fetch_matches returns MatchIdentity list."""
    app = create_stub_app()
    client = TestClient(app)
    adapter = StubPlatformAdapter()
    # Patch _fetch_json to use TestClient
    original_fetch = adapter._fetch_json
    def patched_fetch(path: str):
        response = client.get(path)
        response.raise_for_status()
        return response.json()
    adapter._fetch_json = patched_fetch
    try:
        matches = adapter.fetch_matches()
        assert isinstance(matches, list)
        assert len(matches) >= 2
        for m in matches:
            assert isinstance(m, MatchIdentity)
            assert m.match_id
        # Should be sorted
        match_ids = [m.match_id for m in matches]
        assert match_ids == sorted(match_ids)
    finally:
        adapter.close()


def test_stub_connector_fetch_match_data():
    """Stub connector fetch_match_data returns IngestedMatchData."""
    app = create_stub_app()
    client = TestClient(app)
    adapter = StubPlatformAdapter()
    # Patch _fetch_json to use TestClient
    def patched_fetch(path: str):
        response = client.get(path)
        response.raise_for_status()
        return response.json()
    adapter._fetch_json = patched_fetch
    try:
        data = adapter.fetch_match_data("stub_platform_match_001")
        assert data is not None
        assert isinstance(data, IngestedMatchData)
        assert data.match_id == "stub_platform_match_001"
        assert data.home_team == "North FC"
        assert data.away_team == "South United"
        assert isinstance(data.odds_1x2, dict)
        assert set(data.odds_1x2.keys()) >= {"home", "draw", "away"}
    finally:
        adapter.close()


def test_stub_connector_fetch_match_data_not_found():
    """Stub connector returns None for unknown match_id."""
    app = create_stub_app()
    client = TestClient(app)
    adapter = StubPlatformAdapter()
    # Patch _fetch_json to use TestClient (returns {} for 404)
    def patched_fetch(path: str):
        response = client.get(path)
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json()
    adapter._fetch_json = patched_fetch
    try:
        data = adapter.fetch_match_data("unknown_match_xyz")
        assert data is None
    finally:
        adapter.close()


def test_stub_connector_requires_live_io_allowed():
    """Stub connector is blocked when LIVE_IO_ALLOWED is false (not a RecordedPlatformAdapter)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        adapter = get_connector_safe("stub_platform")
        assert adapter is None


def test_stub_connector_allowed_when_live_io_enabled():
    """Stub connector is allowed when LIVE_IO_ALLOWED is true and shadow mode with baseline."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        with execution_mode_context("shadow"):
            adapter = get_connector_safe("stub_platform")
        assert adapter is not None
        assert isinstance(adapter, StubPlatformAdapter)


def test_stub_connector_parse_match_data_valid():
    """Stub connector parse_match_data handles valid fixture data."""
    adapter = StubPlatformAdapter()
    raw = {
        "match_id": "test_001",
        "home_team": "Team A",
        "away_team": "Team B",
        "competition": "Test League",
        "kickoff_utc": "2025-10-01T15:00:00Z",
        "odds_1x2": {"home": 2.0, "draw": 3.0, "away": 4.0},
        "status": "scheduled",
    }
    data = adapter._parse_match_data(raw)
    assert isinstance(data, IngestedMatchData)
    assert data.match_id == "test_001"
    assert data.home_team == "Team A"


def test_stub_connector_parse_match_data_missing_field():
    """Stub connector parse_match_data raises ValueError for missing required fields."""
    adapter = StubPlatformAdapter()
    raw = {"match_id": "test_001"}  # missing other fields
    with pytest.raises(ValueError, match="home_team"):
        adapter._parse_match_data(raw)
