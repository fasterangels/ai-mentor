"""
Integration test: run burn-in-run in dry mode and generate summary from result.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

_tools = _backend.parent / "tools"
if str(_tools) not in sys.path:
    sys.path.insert(0, str(_tools))

import pytest
from fastapi.testclient import TestClient

import models  # noqa: F401
from core.database import dispose_database, get_database_manager, init_database
from dev.stub_server import create_stub_app
from models.base import Base
from runner.burn_in_ops_runner import run_burn_in_ops
from burn_in_summary import format_burn_in_summary, load_latest_bundle


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
async def test_burn_in_run_dry_mode_then_summary(test_db, stub_client, tmp_path) -> None:
    """Run burn-in-run in dry mode; build bundle-like dict and generate summary; assert plan produced and summary contains key fields."""
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

            reports_dir = tmp_path / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            index_path = reports_dir / "index.json"
            index_path.write_text("{}", encoding="utf-8")

            async with get_database_manager().session() as session:
                result = await run_burn_in_ops(
                    session,
                    connector_name="stub_live_platform",
                    enable_activation=False,
                    dry_run=True,
                    reports_dir=str(reports_dir),
                    index_path=str(index_path),
                )

            assert not result.get("error"), result.get("detail", result.get("error"))
            run_id = result.get("run_id")
            assert run_id

            # Build bundle-like dict from dry-run result and generate summary
            bundle = {
                "run_id": run_id,
                "summary": {
                    "run_id": run_id,
                    "status": result.get("status", "ok"),
                    "alerts_count": result.get("alerts_count", 0),
                    "activated": result.get("activated", False),
                    "matches_count": result.get("matches_count", 0),
                    "connector_name": result.get("connector_name", "?"),
                },
                "live_compare": result.get("live_compare") or {},
                "live_analyze": result.get("live_analyze") or {},
            }
            summary_text = format_burn_in_summary(bundle)
            assert "Run:" in summary_text
            assert run_id in summary_text
            assert "Status:" in summary_text
            assert "Alerts:" in summary_text
            assert "Activated:" in summary_text
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_load_latest_bundle_and_summary(test_db, stub_client, tmp_path) -> None:
    """Run burn-in-run (no dry_run), then load_latest_bundle and format_burn_in_summary."""
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

            reports_dir = tmp_path / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            async with get_database_manager().session() as session:
                result = await run_burn_in_ops(
                    session,
                    connector_name="stub_live_platform",
                    enable_activation=False,
                    dry_run=False,
                    reports_dir=str(reports_dir),
                    index_path=str(reports_dir / "index.json"),
                )

            assert not result.get("error"), result.get("detail", result.get("error"))
            run_id = result.get("run_id")
            assert run_id

            bundle = load_latest_bundle(reports_dir)
            assert bundle is not None
            assert bundle.get("run_id") == run_id or (bundle.get("summary") or {}).get("run_id") == run_id
            summary_text = format_burn_in_summary(bundle)
            assert "Run:" in summary_text
            assert run_id in summary_text
        finally:
            if original:
                register_connector("stub_live_platform", original)
