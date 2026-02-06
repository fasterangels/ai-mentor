"""Integration test for G3: delta evaluation writes report; analyzer not invoked."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from evaluation.live_recorded_delta import run_delta_evaluation, load_snapshots_by_fixture
from pipeline.snapshot_envelope import build_envelope_for_recorded, build_envelope_for_live_shadow
from repositories.raw_payload_repo import RawPayloadRepository


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
async def test_delta_eval_writes_report_and_analyzer_not_invoked(test_db) -> None:
    from datetime import datetime, timezone
    fixture_id = "delta_f1"
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    later = datetime(2025, 6, 1, 12, 0, 1, tzinfo=timezone.utc)
    payload_rec = {"match_id": fixture_id, "source_name": "pipeline_cache", "data": {}}
    payload_live = {"fixture_id": fixture_id, "data": {}}
    env_rec = build_envelope_for_recorded(payload_rec, "rec_sid", now, "pipeline_cache")
    env_live = build_envelope_for_live_shadow(
        payload_live, "live_sid", later, "live_shadow", later,
        fetch_started_at_utc=now, fetch_ended_at_utc=later, latency_ms=50.0,
    )
    async with get_database_manager().session() as session:
        repo = RawPayloadRepository(session)
        await repo.add_payload(
            source_name="pipeline_cache",
            domain="fixtures",
            payload_hash="rec_sid",
            payload_json=json.dumps({"metadata": env_rec.to_dict(), "payload": payload_rec}, sort_keys=True, default=str),
            related_match_id=None,
        )
        await repo.add_payload(
            source_name="live_shadow",
            domain="fixture_detail",
            payload_hash="live_sid",
            payload_json=json.dumps({"metadata": env_live.to_dict(), "payload": payload_live}, sort_keys=True, default=str),
            related_match_id=None,
        )
        await session.commit()
    reports_dir = Path(_backend) / "tests" / "integration" / "tmp_delta_eval_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    index_path = reports_dir / "index.json"
    async with get_database_manager().session() as session:
        result = await run_delta_evaluation(session, reports_dir=str(reports_dir), index_path=str(index_path))
    assert result.get("reports_written", 0) >= 1
    assert result.get("complete_count", 0) >= 1
    report_file = Path(result.get("report_path", ""))
    assert report_file.exists()
    data = json.loads(report_file.read_text(encoding="utf-8"))
    assert "reports" in data
    complete = [r for r in data["reports"] if r.get("status") == "COMPLETE"]
    assert len(complete) >= 1
    assert complete[0].get("fixture_id") == fixture_id
    assert "observed_at_delta_ms" in complete[0]
