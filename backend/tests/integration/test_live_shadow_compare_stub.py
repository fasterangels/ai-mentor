"""
Integration test: live shadow compare using stub_live_platform (live = TestClient, recorded = fixtures).
Validates diff report structure and deterministic ordering. No external network.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

from dev.stub_server import create_stub_app
from ingestion.connectors.platform_base import IngestedMatchData
from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
from ingestion.fixtures.validator import validate_fixtures
from reports.live_shadow_compare import ingested_to_dict
from runner.live_shadow_compare_runner import run_live_shadow_compare


def _load_stub_live_fixtures() -> list[tuple[str, IngestedMatchData | None]]:
    """Load stub_live_platform fixtures and return (match_id, IngestedMatchData) list."""
    from ingestion.connectors.sample_platform import SamplePlatformAdapter
    fixtures_dir = _backend / "ingestion" / "fixtures" / "stub_live_platform"
    if not fixtures_dir.exists():
        return []
    adapter = SamplePlatformAdapter(fixtures_dir=fixtures_dir)
    raw_list = adapter.load_fixtures()
    out = []
    for raw in raw_list:
        try:
            parsed = adapter.parse_fixture(raw)
            out.append((parsed.match_id, parsed))
        except ValueError:
            pass
    return out


@pytest.mark.asyncio
async def test_live_shadow_compare_stub_live_structure_and_ordering() -> None:
    """Run compare with stub_live (TestClient) vs recorded (fixtures). Assert diff report structure and deterministic order."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        stub_client = TestClient(create_stub_app())
        adapter_live = StubLivePlatformAdapter(base_url="http://testserver")
        adapter_live._client = stub_client

        recorded_items = _load_stub_live_fixtures()
        assert len(recorded_items) >= 1
        match_ids = sorted(mid for mid, _ in recorded_items)

        live_list = []
        for mid in match_ids:
            d = adapter_live.fetch_match_data(mid)
            live_list.append({"match_id": mid, "data": ingested_to_dict(d) if d else None})
        recorded_list = [{"match_id": mid, "data": ingested_to_dict(d) if d else None} for mid, d in recorded_items]
        live_list.sort(key=lambda x: x["match_id"])
        recorded_list.sort(key=lambda x: x["match_id"])

        result = run_live_shadow_compare(
            live_snapshots=live_list,
            recorded_snapshots=recorded_list,
            reports_dir=str(_backend / "reports"),
        )

    assert result.get("error") is None
    assert "diff_report" in result
    diff = result["diff_report"]
    assert "identity_parity" in diff
    assert "odds_presence_parity" in diff
    assert "odds_value_drift" in diff
    assert "schema_drift" in diff
    assert "summary" in diff
    assert "alerts" in diff
    assert "match_ids" in result
    assert result["match_ids"] == sorted(result["match_ids"])


def test_stub_live_fixtures_exist_and_valid() -> None:
    """Stub_live_platform fixtures exist and pass validator."""
    fixtures_dir = _backend / "ingestion" / "fixtures" / "stub_live_platform"
    assert fixtures_dir.is_dir()
    report = validate_fixtures(fixtures_dir)
    assert report.ok is True, report.errors
