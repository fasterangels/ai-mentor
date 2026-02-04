"""
Pipeline smoke test: shadow pipeline e2e with stub_live_platform against local stub (no real network).
Uses fixtures data via in-process stub server (TestClient).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from pipeline.shadow_pipeline import run_shadow_pipeline
from dev.stub_server import create_stub_app
from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
from ingestion.registry import register_connector


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
    """Local stub server (no external IO)."""
    return TestClient(create_stub_app())


@pytest.mark.asyncio
async def test_shadow_pipeline_stub_live_e2e_no_network(test_db, stub_client) -> None:
    """Shadow pipeline runs e2e with stub_live_platform using in-process stub (no real network)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        adapter = StubLivePlatformAdapter()
        def patched_get(path: str):
            r = stub_client.get(path)
            r.raise_for_status()
            return r.json()
        adapter._get = patched_get
        from ingestion.registry import get_connector
        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)
            now = datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
            async with get_database_manager().session() as session:
                report = await run_shadow_pipeline(
                    session,
                    connector_name="stub_live_platform",
                    match_id="stub_live_001",
                    final_score={"home": 2, "away": 1},
                    status="FINAL",
                    now_utc=now,
                )
            assert report.get("error") is None
            assert "ingestion" in report
            assert report["ingestion"].get("payload_checksum") is not None
            assert "analysis" in report
            assert "resolution" in report
            assert "evaluation_report_checksum" in report
            assert "proposal" in report
            assert "audit" in report
        finally:
            adapter.close()
            if original is not None:
                register_connector("stub_live_platform", original)
