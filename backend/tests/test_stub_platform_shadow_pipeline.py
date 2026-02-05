"""
E2E: full shadow pipeline with connector stub_platform (live IO via HTTP stub server).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from pipeline.shadow_pipeline import run_shadow_pipeline
from ingestion.stub_server import create_stub_app


@pytest.fixture
def test_db():
    """In-memory SQLite with all tables."""
    async def _setup():
        await init_database("sqlite+aiosqlite:///:memory:")
        engine = get_database_manager().engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        await dispose_database()

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


@pytest.fixture
def stub_client():
    """Create test client for stub server."""
    app = create_stub_app()
    return TestClient(app)


@pytest.mark.asyncio
async def test_shadow_pipeline_stub_platform_produces_full_report(test_db, stub_client) -> None:
    """Full shadow pipeline runs using stub_platform (requires LIVE_IO_ALLOWED) and produces PipelineReport."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        # Patch stub connector to use test client
        from ingestion.connectors.stub_platform import StubPlatformAdapter
        from ingestion.registry import register_connector
        original_adapter = StubPlatformAdapter()
        stub_adapter = StubPlatformAdapter()
        # Patch _fetch_json to use TestClient
        def patched_fetch(path: str):
            response = stub_client.get(path)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            return response.json()
        stub_adapter._fetch_json = patched_fetch
        register_connector("stub_platform", stub_adapter)
        try:
            now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_platform",
                    match_id="stub_platform_match_001",
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=now,
                )

            assert report.get("error") is None
            assert "ingestion" in report
            assert report["ingestion"].get("payload_checksum") is not None
            assert "analysis" in report
            assert "markets_picks_confidences" in report["analysis"]
            assert "resolution" in report
            assert "market_outcomes" in report["resolution"]
            assert "evaluation_report_checksum" in report
            assert report["evaluation_report_checksum"] is not None
            assert "proposal" in report
            assert "proposal_checksum" in report["proposal"]
            assert "audit" in report
            assert "changed_count" in report["audit"]
            assert "snapshots_checksum" in report["audit"]
        finally:
            stub_adapter.close()
            register_connector("stub_platform", original_adapter)


@pytest.mark.asyncio
async def test_shadow_pipeline_stub_platform_blocked_without_live_io(test_db, stub_client) -> None:
    """Shadow pipeline with stub_platform is blocked when LIVE_IO_ALLOWED is false."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        async with get_database_manager().session() as session:
            report = await run_shadow_pipeline(
                session,
                connector_name="stub_platform",
                match_id="stub_platform_match_001",
                final_score={"home": 2, "away": 1},
                status="FINAL",
                now_utc=now,
            )

        assert report.get("error") == "CONNECTOR_NOT_FOUND"
        detail = report.get("detail", "").lower()
        assert "live io not allowed" in detail or "not available" in detail
