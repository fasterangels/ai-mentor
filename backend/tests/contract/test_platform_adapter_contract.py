"""
Reusable contract tests for platform adapters.
Use assert_adapter_contract(adapter_name, fixtures_dir) in each adapter's test module.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.connectors.platform_base import IngestedMatchData, MatchIdentity
from ingestion.registry import get_connector


def assert_adapter_contract(adapter_name: str, fixtures_dir: str) -> None:
    """
    Reusable contract assertions for a RecordedPlatformAdapter.
    adapter_name: registry key (e.g. "sample_platform").
    fixtures_dir: path relative to backend (e.g. "ingestion/fixtures/sample_platform").
    """
    adapter = get_connector(adapter_name)
    assert adapter is not None, f"Adapter {adapter_name!r} not registered"

    # 1) Adapter loads fixtures
    fixtures = adapter.load_fixtures()
    assert isinstance(fixtures, list), "load_fixtures must return a list"
    assert len(fixtures) >= 1, "At least one fixture required"
    for f in fixtures:
        assert isinstance(f, dict), "Each fixture must be a dict"

    # 2) fetch_matches deterministic (same order twice)
    ids1 = [m.match_id for m in adapter.fetch_matches()]
    ids2 = [m.match_id for m in adapter.fetch_matches()]
    assert ids1 == ids2, "fetch_matches must be deterministic"
    assert ids1 == sorted(ids1), "fetch_matches must return match_ids in sorted order"

    # 3) fetch_match_data returns valid IngestedMatchData for at least one fixture
    match_id = ids1[0]
    data = adapter.fetch_match_data(match_id)
    assert data is not None, f"fetch_match_data({match_id!r}) must return data"
    assert isinstance(data, IngestedMatchData)
    assert data.match_id == match_id
    assert data.home_team and data.away_team and data.competition
    assert "T" in data.kickoff_utc or "Z" in data.kickoff_utc or "+" in data.kickoff_utc
    assert set(data.odds_1x2.keys()) >= {"home", "draw", "away"}
    assert all(isinstance(v, (int, float)) and v > 0 for v in data.odds_1x2.values())

    # 4) Missing required fields raise ValueError
    with pytest.raises(ValueError):
        adapter.parse_fixture({})
    with pytest.raises(ValueError):
        adapter.parse_fixture({"match_id": "x"})  # missing others

    # 5) No network: adapter module must not import httpx, requests, or socket
    mod_name = adapter.__class__.__module__
    mod = importlib.import_module(mod_name)
    mod_dict = getattr(mod, "__dict__", {})
    assert "httpx" not in mod_dict, f"Adapter module {mod_name} must not import httpx"
    assert "requests" not in mod_dict, f"Adapter module {mod_name} must not import requests"
    assert "socket" not in mod_dict, f"Adapter module {mod_name} must not import socket"
