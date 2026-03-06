"""
Integration test for G1 live shadow adapter: FakeLiveClient, snapshots written, no analysis.
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
from sqlalchemy import func, select

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.analysis_run import AnalysisRun
from models.base import Base
from models.raw_payload import RawPayload
from pipeline.live_snapshot.live_source_client import FakeLiveClient
from runner.live_shadow_runner import run_live_shadow_mode


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


@pytest.mark.asyncio
async def test_live_shadow_mode_writes_snapshots_no_analysis(test_db, monkeypatch) -> None:
    """Run live-shadow with FakeLiveClient: snapshots written, metadata present, no analysis runs."""
    monkeypatch.setenv("LIVE_IO_ALLOWED", "true")
    monkeypatch.setenv("SNAPSHOT_WRITES_ALLOWED", "true")

    fixtures = [
        {"fixture_id": "int_f1", "home_team": "A", "away_team": "B"},
        {"fixture_id": "int_f2", "home_team": "C", "away_team": "D"},
    ]
    client = FakeLiveClient(fixtures=fixtures)

    async with get_database_manager().session() as session:
        r = select(func.count()).select_from(AnalysisRun)
        before = (await session.execute(r)).scalar() or 0
        result = await run_live_shadow_mode(session, client)
        after = (await session.execute(r)).scalar() or 0

    assert result.get("error") is None
    assert result.get("snapshots_written") >= 1
    assert result.get("fetch_ok") == 2
    assert after == before, "Live-shadow must not create any analysis runs"

    async with get_database_manager().session() as session:
        stmt = select(RawPayload).where(RawPayload.source_name == "live_shadow").limit(2)
        result_q = await session.execute(stmt)
        rows = result_q.scalars().all()
    assert len(rows) >= 1
    row = rows[0]
    envelope = json.loads(row.payload_json)
    assert "metadata" in envelope
    meta = envelope["metadata"]
    assert meta.get("snapshot_type") == "live_shadow"
    assert meta.get("source", {}).get("class") == "LIVE_SHADOW"
    assert "observed_at_utc" in meta
    assert "payload_checksum" in meta
    assert "latency_ms" in meta
    assert meta.get("schema_version") == 1
    assert "envelope_checksum" in meta
