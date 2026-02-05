"""
Shadow pipeline e2e with real_provider in recorded mode (fixtures only, no network).
Asserts report includes live_io_metrics and guardrails section.
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

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from pipeline.shadow_pipeline import run_shadow_pipeline
from runner.shadow_runner import run_shadow_batch


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


@pytest.mark.asyncio
async def test_shadow_pipeline_real_provider_recorded_e2e_no_network(test_db) -> None:
    """Shadow pipeline runs e2e with real_provider using fixtures only (no live calls)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "0")
        m.delenv("LIVE_IO_ALLOWED", raising=False)
        now = datetime(2025, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        async with get_database_manager().session() as session:
            report = await run_shadow_pipeline(
                session,
                connector_name="real_provider",
                match_id="real_provider_001",
                final_score={"home": 1, "away": 1},
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


@pytest.mark.asyncio
async def test_shadow_batch_real_provider_includes_live_io_metrics_and_guardrails(test_db) -> None:
    """Shadow batch with real_provider (recorded) includes live_io_metrics and live_io_alerts (may be empty/zero)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("REAL_PROVIDER_LIVE", "0")
        m.delenv("LIVE_IO_ALLOWED", raising=False)
        now = datetime(2025, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        async with get_database_manager().session() as session:
            report = await run_shadow_batch(
                session,
                connector_name="real_provider",
                match_ids=["real_provider_001"],
                now_utc=now,
                dry_run=True,
            )
    assert report.get("error") is None
    assert "live_io_metrics" in report
    assert "counters" in report["live_io_metrics"]
    assert "latency_ms" in report["live_io_metrics"]
    assert "live_io_alerts" in report
    assert isinstance(report["live_io_alerts"], list)
