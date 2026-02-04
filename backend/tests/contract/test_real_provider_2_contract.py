"""
Contract tests for real_provider_2: validator-compliant fixtures and recorded-first connector.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import IngestedMatchData, MatchIdentity
from ingestion.connectors.real_provider_2 import RealProvider2Adapter
from ingestion.fixtures.validator import validate_fixtures
from ingestion.live_io import get_connector_safe


def test_real_provider_2_fixtures_pass_validator() -> None:
    """Fixtures in real_provider_2 directory pass validator."""
    fixtures_dir = Path(__file__).resolve().parent.parent.parent / "ingestion" / "fixtures" / "real_provider_2"
    report = validate_fixtures(fixtures_dir)
    assert report.ok, f"Validator errors: {report.errors}"


def test_real_provider_2_adapter_fetch_matches() -> None:
    """RealProvider2Adapter fetch_matches returns MatchIdentity list from fixtures."""
    adapter = RealProvider2Adapter()
    matches = adapter.fetch_matches()
    assert isinstance(matches, list)
    assert all(isinstance(m, MatchIdentity) for m in matches)
    ids = sorted(m.match_id for m in matches)
    assert "real_provider_2_match_001" in ids
    assert "real_provider_2_match_002" in ids


def test_real_provider_2_adapter_fetch_match_data() -> None:
    """RealProvider2Adapter fetch_match_data returns IngestedMatchData."""
    adapter = RealProvider2Adapter()
    data = adapter.fetch_match_data("real_provider_2_match_001")
    assert data is not None
    assert isinstance(data, IngestedMatchData)
    assert data.match_id == "real_provider_2_match_001"
    assert data.home_team == "East City"
    assert data.away_team == "West United"
    assert "odds_1x2" in dir(data) and data.odds_1x2["home"] == 2.05


def test_real_provider_2_get_connector_safe_recorded_first() -> None:
    """get_connector_safe returns real_provider_2 without LIVE_IO_ALLOWED (recorded-first)."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("LIVE_IO_ALLOWED", raising=False)
        m.delenv("REAL_PROVIDER_2_LIVE", raising=False)
        adapter = get_connector_safe("real_provider_2")
    assert adapter is not None
    assert adapter.name == "real_provider_2"
