"""
Integration tests for G2: recorded and live_shadow snapshots carry envelope; legacy read defaults.
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
from sqlalchemy import select

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from models.raw_payload import RawPayload
from pipeline.cache import cache_payload, get_cached_payload
from pipeline.snapshot_envelope import parse_payload_json


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
async def test_recorded_cache_writes_envelope_and_read_back(test_db) -> None:
    """Recorded snapshot with G2 envelope: write envelope+payload (no match FK); get_cached_payload returns payload."""
    import hashlib
    from datetime import datetime, timezone
    from pipeline.snapshot_envelope import build_envelope_for_recorded
    from repositories.raw_payload_repo import RawPayloadRepository

    cache_key = hashlib.sha256("g2_match_1:fixtures:24".encode()).hexdigest()[:16]
    payload = {"source_name": "consensus", "data": {"match_id": "g2_match_1"}, "fetched_at_utc": "2025-01-01T00:00:00Z"}
    now = datetime.now(timezone.utc)
    envelope = build_envelope_for_recorded(payload, cache_key, now, "pipeline_cache")
    payload_json = json.dumps(
        {"metadata": envelope.to_dict(), "payload": payload},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    async with get_database_manager().session() as session:
        repo = RawPayloadRepository(session)
        await repo.add_payload(
            source_name="pipeline_cache",
            domain="fixtures",
            payload_hash=cache_key,
            payload_json=payload_json,
            related_match_id=None,
        )
        await session.commit()

    async with get_database_manager().session() as session:
        cached = await get_cached_payload(session, "g2_match_1", "fixtures", 24)
    assert cached is not None
    assert cached.get("source_name") == "consensus"
    async with get_database_manager().session() as session:
        from repositories.raw_payload_repo import RawPayloadRepository
        repo = RawPayloadRepository(session)
        row = await repo.get_by_hash(cache_key)
    assert row is not None
    envelope = json.loads(row.payload_json)
    assert "metadata" in envelope
    meta = envelope["metadata"]
    assert meta.get("snapshot_type") == "recorded"
    assert meta.get("source", {}).get("class") == "RECORDED"
    assert "created_at_utc" in meta
    assert "payload_checksum" in meta
    assert "observed_at_utc" in meta
    assert meta.get("schema_version") == 1
    assert "envelope_checksum" in meta


@pytest.mark.asyncio
async def test_legacy_payload_parse_defaults_no_crash(test_db) -> None:
    """Reading legacy payload_json (no envelope) returns default metadata and payload."""
    from datetime import datetime, timezone
    from repositories.raw_payload_repo import RawPayloadRepository

    legacy_json = json.dumps({"source_name": "old", "data": {}})
    async with get_database_manager().session() as session:
        repo = RawPayloadRepository(session)
        await repo.add_payload(
            source_name="pipeline_cache",
            domain="fixtures",
            payload_hash="legacy_hash_1",
            payload_json=legacy_json,
            related_match_id=None,
        )
        await session.commit()

    async with get_database_manager().session() as session:
        row = (await RawPayloadRepository(session).get_by_hash("legacy_hash_1"))
    assert row is not None
    meta, payload = parse_payload_json(row.payload_json, created_at_utc_fallback=row.fetched_at_utc)
    assert meta["snapshot_type"] == "recorded"
    assert meta["schema_version"] == 0
    assert payload == {"source_name": "old", "data": {}}
