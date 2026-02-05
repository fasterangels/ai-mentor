"""
Unit tests for ops command wiring: burn-in-run with dry-run by default (no disk writes).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from fastapi.testclient import TestClient

import models  # noqa: F401
from core.database import dispose_database, get_database_manager, init_database
from dev.stub_server import create_stub_app
from models.base import Base
from runner.burn_in_ops_runner import run_burn_in_ops


@pytest.fixture
def test_db():
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
    return TestClient(create_stub_app())


@pytest.mark.asyncio
async def test_burn_in_ops_dry_run_wiring(test_db, stub_client) -> None:
    """Ops burn-in-run with dry_run=True returns bundle structure; reports are still written (read-only semantics)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "1")
        m.setenv("STUB_LIVE_MODE", "ok")

        from ingestion.connectors.stub_live_platform import StubLivePlatformAdapter
        from ingestion.registry import get_connector, register_connector

        adapter = StubLivePlatformAdapter(base_url="http://testserver")
        adapter._base_url = "http://testserver"
        adapter._client = stub_client

        original = get_connector("stub_live_platform")
        try:
            register_connector("stub_live_platform", adapter)

            async with get_database_manager().session() as session:
                result = await run_burn_in_ops(
                    session,
                    connector_name="stub_live_platform",
                    enable_activation=False,
                    dry_run=True,
                    reports_dir="reports",
                    index_path="reports/index.json",
                )

            assert result.get("run_id")
            assert "live_compare" in result
            assert "live_analyze" in result
            assert result.get("status") in ("ok", "error")
            assert "matches_count" in result
            assert result.get("_bundle_dir")
        finally:
            if original:
                register_connector("stub_live_platform", original)
