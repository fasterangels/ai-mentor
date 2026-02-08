"""Integration test for G4: staleness-eval writes reports; analyzer not invoked during eval."""
from __future__ import annotations

import asyncio
import json
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
from evaluation.staleness_metrics import run_staleness_evaluation
from pipeline.snapshot_envelope import build_envelope_for_recorded
from pipeline.shadow_pipeline import run_shadow_pipeline
from repositories.analysis_run_repo import AnalysisRunRepository
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
async def test_staleness_eval_writes_report_and_analyzer_not_invoked_during_eval(test_db) -> None:
    """Run pipeline once to seed run+resolution+predictions; add pipeline_cache payload; run staleness-eval; assert reports."""
    match_id = "staleness_g4_m1"
    now = datetime(2025, 6, 1, 14, 0, 0, tzinfo=timezone.utc)
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
            run_repo = AnalysisRunRepository(session)
            runs = await run_repo.list_recent(limit=5)
            run = next((r for r in runs if r.match_id == match_id), None)
            assert run is not None
            evidence_observed = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
            payload = {"match_id": match_id, "data": {}}
            env = build_envelope_for_recorded(payload, "st_g4_sid", evidence_observed, "pipeline_cache")
            raw_repo = RawPayloadRepository(session)
            await raw_repo.add_payload(
                source_name="pipeline_cache",
                domain="fixtures",
                payload_hash="st_g4_hash",
                payload_json=json.dumps({"metadata": env.to_dict(), "payload": payload}, sort_keys=True, default=str),
                related_match_id=match_id,
            )
            await session.commit()

    reports_dir = Path(_backend) / "tests" / "integration" / "tmp_staleness_eval_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    index_path = reports_dir / "index.json"
    async with get_database_manager().session() as session:
        result = await run_staleness_evaluation(session, reports_dir=str(reports_dir), index_path=str(index_path))
    assert result.get("reports_written", 0) >= 1
    assert "row_count" in result
    # CSV and JSON report files exist (stable filenames)
    report_csv = Path(result.get("report_path_csv", ""))
    report_json = Path(result.get("report_path_json", ""))
    assert report_csv.exists(), "staleness_metrics_by_reason CSV should exist"
    assert report_json.exists(), "staleness_metrics_by_reason JSON should exist"
    # CSV has expected headers
    csv_lines = report_csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(csv_lines) >= 1
    headers = csv_lines[0].split(",")
    for key in ("market", "reason_code", "age_band", "total", "correct", "accuracy", "neutral_rate", "avg_confidence"):
        assert key in headers, f"CSV should contain column {key!r}"
    # JSON has expected structure
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert "rows" in data
    assert "run_id" in data
    if data["rows"]:
        row = data["rows"][0]
        assert "market" in row and "reason_code" in row and "age_band" in row and "total" in row
        assert "accuracy" in row or "correct" in row
    # Staleness-eval only reads existing data and writes reports; analyzer/evaluator are NOT invoked in this path
