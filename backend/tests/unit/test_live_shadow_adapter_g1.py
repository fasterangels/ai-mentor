"""
Unit tests for G1 live shadow read adapter: block when flags off, checksum stability, dedup.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from pipeline.live_snapshot.live_shadow_adapter import run_live_shadow_read
from pipeline.live_snapshot.live_source_client import FakeLiveClient


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
async def test_live_shadow_blocked_when_live_io_not_allowed(test_db) -> None:
    """When LIVE_IO_ALLOWED=false, adapter returns error (no exception)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "0")
        m.setenv("SNAPSHOT_WRITES_ALLOWED", "1")
        client = FakeLiveClient(fixtures=[{"fixture_id": "f1", "name": "Test"}])
        async with get_database_manager().session() as session:
            result = await run_live_shadow_read(session, client)
    assert result.get("error") == "LIVE_IO_NOT_ALLOWED"
    assert result.get("snapshots_written") == 0
    assert "LIVE_IO_ALLOWED" in (result.get("detail") or "")


@pytest.mark.asyncio
async def test_live_shadow_blocked_when_snapshot_writes_not_allowed(test_db) -> None:
    """When SNAPSHOT_WRITES_ALLOWED=false, adapter returns error."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("LIVE_IO_ALLOWED", "true")
        m.setenv("SNAPSHOT_WRITES_ALLOWED", "0")
        client = FakeLiveClient(fixtures=[{"fixture_id": "f1"}])
        async with get_database_manager().session() as session:
            result = await run_live_shadow_read(session, client)
    assert result.get("error") == "SNAPSHOT_WRITES_NOT_ALLOWED"
    assert result.get("snapshots_written") == 0


@pytest.mark.asyncio
async def test_live_shadow_checksum_stable_and_dedup(test_db, monkeypatch) -> None:
    """Identical payload: first run writes 1, second run dedupes (deduped=1, snapshots_written=0)."""
    monkeypatch.setenv("LIVE_IO_ALLOWED", "true")
    monkeypatch.setenv("SNAPSHOT_WRITES_ALLOWED", "true")
    fixture = {"fixture_id": "dedup_f1", "title": "Same"}
    client = FakeLiveClient(fixtures=[fixture])
    async with get_database_manager().session() as session:
        result1 = await run_live_shadow_read(session, client)
    assert result1.get("error") is None
    assert result1.get("snapshots_written") == 1
    assert result1.get("deduped") == 0

    async with get_database_manager().session() as session:
        result2 = await run_live_shadow_read(session, client)
    assert result2.get("error") is None
    assert result2.get("snapshots_written") == 0
    assert result2.get("deduped") == 1
