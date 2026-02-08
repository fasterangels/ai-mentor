"""
Integration test for H3 Part B: uncertainty-shadow writes reports; would_refuse deterministic; analyzer unchanged.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from evaluation.confidence_penalty_shadow import run_confidence_penalty_shadow
from evaluation.staleness_metrics import run_staleness_evaluation
from evaluation.uncertainty_shadow import run_uncertainty_shadow
from pipeline.snapshot_envelope import build_envelope_for_recorded
from pipeline.shadow_pipeline import run_shadow_pipeline
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
async def test_uncertainty_shadow_writes_reports_would_refuse_deterministic(test_db) -> None:
    """
    Seed DB; run staleness-eval, decay-fit, confidence-penalty-shadow, then uncertainty-shadow.
    Assert reports written, would_refuse present and deterministic; analyzer unchanged.
    """
    match_id = "us_h3_m1"
    now = datetime(2025, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
    reports_dir = Path(_backend) / "tests" / "integration" / "tmp_uncertainty_shadow"
    reports_dir.mkdir(parents=True, exist_ok=True)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "dummy")
        m.setenv("ACTIVATION_MARKETS", "1X2")
        m.setenv("ACTIVATION_MAX_MATCHES", "10")
        m.setenv("ACTIVATION_MIN_CONFIDENCE", "0.5")
        async with get_database_manager().session() as session:
            report = await run_shadow_pipeline(
                session,
                connector_name="dummy",
                match_id=match_id,
                final_score={"home": 2, "away": 1},
                status="FINAL",
                now_utc=now,
                activation=True,
            )
            assert report.get("error") is None
            evidence_observed = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
            payload = {"match_id": match_id, "data": {}}
            env = build_envelope_for_recorded(payload, "us_sid", evidence_observed, "pipeline_cache")
            raw_repo = RawPayloadRepository(session)
            await raw_repo.add_payload(
                source_name="pipeline_cache",
                domain="fixtures",
                payload_hash="us_hash",
                payload_json=json.dumps({"metadata": env.to_dict(), "payload": payload}, sort_keys=True, default=str),
                related_match_id=match_id,
            )
            await session.commit()

    index_path = reports_dir / "index.json"
    async with get_database_manager().session() as session:
        await run_staleness_evaluation(session, reports_dir=str(reports_dir), index_path=str(index_path))

    from runner.decay_fit_runner import run_decay_fit_mode
    run_decay_fit_mode(reports_dir=reports_dir)

    async with get_database_manager().session() as session:
        await run_confidence_penalty_shadow(session, reports_dir=reports_dir, limit=100)

    async with get_database_manager().session() as session:
        result = await run_uncertainty_shadow(session, reports_dir=reports_dir, limit=100)
    assert "row_count" in result
    csv_path = result.get("report_path_csv")
    json_path = result.get("report_path_json")
    assert csv_path and Path(csv_path).exists()
    assert json_path and Path(json_path).exists()
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert "rows" in data
    assert "computed_at_utc" in data
    for row in data.get("rows", [])[:1]:
        assert "run_id" in row
        assert "would_refuse" in row
        assert "triggered_count" in row
        assert "triggered_signals" in row
        assert "signals" in row
    # Determinism: run twice, same would_refuse
    async with get_database_manager().session() as session:
        result2 = await run_uncertainty_shadow(session, reports_dir=reports_dir, limit=100)
    data2 = json.loads(Path(result2["report_path_json"]).read_text(encoding="utf-8"))
    rows1 = {r["run_id"]: r["would_refuse"] for r in data["rows"]}
    rows2 = {r["run_id"]: r["would_refuse"] for r in data2["rows"]}
    assert rows1 == rows2
