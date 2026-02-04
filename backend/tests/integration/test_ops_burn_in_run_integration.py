"""
Integration test: run ops burn-in-run against stub_live_platform; assert report bundle created and index updated.
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
from reports.index_store import load_index
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
async def test_ops_burn_in_run_creates_bundle_and_updates_index(test_db, stub_client, tmp_path) -> None:
    """Run burn-in-run (no dry_run); assert report bundle under reports/burn_in/<run_id>/ and index entry."""
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
            index_path = reports_dir / "index.json"
            reports_dir.mkdir(parents=True, exist_ok=True)

            async with get_database_manager().session() as session:
                result = await run_burn_in_ops(
                    session,
                    connector_name="stub_live_platform",
                    enable_activation=False,
                    dry_run=False,
                    reports_dir=str(reports_dir),
                    index_path=str(index_path),
                )

            assert not result.get("error"), result.get("detail", result.get("error"))
            run_id = result.get("run_id")
            assert run_id

            bundle_dir = reports_dir / "burn_in" / run_id
            assert bundle_dir.exists()
            assert (bundle_dir / "summary.json").exists()
            assert (bundle_dir / "live_compare.json").exists()
            assert (bundle_dir / "live_analyze.json").exists()

            index = load_index(index_path)
            assert "burn_in_ops_runs" in index
            assert len(index["burn_in_ops_runs"]) >= 1
            assert index["latest_burn_in_ops_run_id"] == run_id
            entry = index["burn_in_ops_runs"][-1]
            assert entry["run_id"] == run_id
            assert "status" in entry
            assert "activated" in entry
            assert entry["activated"] is False
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_ops_burn_in_creates_index_json_when_reports_dir_missing(test_db, stub_client, tmp_path) -> None:
    """Burn-in ops creates reports_dir and index.json when they do not exist (no manual setup)."""
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
            index_path = reports_dir / "index.json"
            assert not reports_dir.exists(), "reports_dir must not exist before run"

            async with get_database_manager().session() as session:
                result = await run_burn_in_ops(
                    session,
                    connector_name="stub_live_platform",
                    enable_activation=False,
                    dry_run=False,
                    reports_dir=str(reports_dir),
                    index_path=str(index_path),
                )

            assert result.get("run_id")
            assert reports_dir.exists(), "reports_dir must be created by runner"
            assert index_path.exists(), "reports/index.json must be created"
            index = load_index(index_path)
            assert "burn_in_ops_runs" in index
            assert len(index["burn_in_ops_runs"]) >= 1, "index must be non-empty after run"
            assert index["latest_burn_in_ops_run_id"] == result["run_id"]
        finally:
            if original:
                register_connector("stub_live_platform", original)


@pytest.mark.asyncio
async def test_ops_burn_in_dry_run_still_writes_reports(test_db, stub_client, tmp_path) -> None:
    """dry_run=True still writes bundle and index (read-only semantics; no activation)."""
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
            index_path = reports_dir / "index.json"

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
            bundle_dir = reports_dir / "burn_in" / run_id
            assert bundle_dir.exists(), "dry_run must still write bundle"
            assert (bundle_dir / "summary.json").exists()
            assert (bundle_dir / "live_compare.json").exists()
            assert (bundle_dir / "live_analyze.json").exists()
            assert index_path.exists(), "dry_run must still write index.json"
            index = load_index(index_path)
            assert len(index["burn_in_ops_runs"]) >= 1
        finally:
            if original:
                register_connector("stub_live_platform", original)
