"""
Unit tests for real_provider live path gates: blocked unless REAL_PROVIDER_LIVE + LIVE_IO_ALLOWED + required env.
Mock any HTTP call sites; zero real IO.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.real_provider import (
    RealProviderAdapter,
    _real_provider_live_config,
    _real_provider_live_enabled,
)

_FIXTURES_DIR = _backend / "ingestion" / "fixtures" / "real_provider"


def test_live_path_blocked_without_real_provider_live() -> None:
    """Live path is not used when REAL_PROVIDER_LIVE is not set."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "0")
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("REAL_PROVIDER_BASE_URL", "https://api.example.com")
        m.setenv("REAL_PROVIDER_API_KEY", "secret")
        adapter = RealProviderAdapter(fixtures_dir=_FIXTURES_DIR)
        assert adapter._use_live() is False
        matches = adapter.fetch_matches()
        assert len(matches) >= 1
        data = adapter.fetch_match_data("real_provider_001")
        assert data is not None
        assert data.match_id == "real_provider_001"


def test_live_path_blocked_without_live_io_allowed() -> None:
    """Live path is not used when LIVE_IO_ALLOWED is false even if REAL_PROVIDER_LIVE is set."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "1")
        m.setenv("LIVE_IO_ALLOWED", "0")
        m.setenv("REAL_PROVIDER_BASE_URL", "https://api.example.com")
        m.setenv("REAL_PROVIDER_API_KEY", "secret")
        adapter = RealProviderAdapter(fixtures_dir=_FIXTURES_DIR)
        assert adapter._use_live() is False


def test_live_config_raises_without_base_url() -> None:
    """_real_provider_live_config raises when REAL_PROVIDER_BASE_URL is missing."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("REAL_PROVIDER_BASE_URL", raising=False)
        m.setenv("REAL_PROVIDER_API_KEY", "key")
        with pytest.raises(RuntimeError, match="REAL_PROVIDER_BASE_URL"):
            _real_provider_live_config()


def test_live_config_raises_without_api_key() -> None:
    """_real_provider_live_config raises when REAL_PROVIDER_API_KEY is missing."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_BASE_URL", "https://api.example.com")
        m.delenv("REAL_PROVIDER_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="REAL_PROVIDER_API_KEY"):
            _real_provider_live_config()


def test_live_fetch_matches_raises_without_gates() -> None:
    """_live_fetch_matches raises when REAL_PROVIDER_LIVE or LIVE_IO_ALLOWED is not set."""
    adapter = RealProviderAdapter(fixtures_dir=_FIXTURES_DIR)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "0")
        m.setenv("LIVE_IO_ALLOWED", "0")
        with pytest.raises(RuntimeError, match="REAL_PROVIDER_LIVE|LIVE_IO_ALLOWED"):
            adapter._live_fetch_matches()


@patch("httpx.Client")
def test_live_fetch_matches_uses_httpx_mock_no_real_io(mock_client_class) -> None:
    """When live is enabled, _live_fetch_matches uses HTTP client (mocked; no real IO)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "1")
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("REAL_PROVIDER_BASE_URL", "https://api.example.com")
        m.setenv("REAL_PROVIDER_API_KEY", "secret")
        mock_response = mock_client_class.return_value.__enter__.return_value.get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "match_id": "live_001",
                "home_team": "A",
                "away_team": "B",
                "competition": "League",
                "kickoff_utc": "2025-12-01T15:00:00+00:00",
                "status": "scheduled",
                "odds_1x2": {"home": 2.0, "draw": 3.0, "away": 3.5},
            }
        ]
        adapter = RealProviderAdapter(fixtures_dir=_FIXTURES_DIR)
        matches = adapter.fetch_matches()
        assert len(matches) == 1
        assert matches[0].match_id == "live_001"
        mock_client_class.return_value.__enter__.return_value.get.assert_called_once()
