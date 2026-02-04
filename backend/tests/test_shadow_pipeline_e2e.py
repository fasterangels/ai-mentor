"""
E2E shadow pipeline: dummy ingestion -> analysis -> attach -> evaluation -> tune -> audit.
Uses in-memory DB; no network. Asserts PipelineReport structure and determinism.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401 - register all models with Base.metadata
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
from pipeline.shadow_pipeline import run_shadow_pipeline


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
async def test_shadow_pipeline_creates_analysis_run_and_resolution(test_db):
    """Run pipeline for dummy-match-1; assert analysis run and snapshot resolution created."""
    from repositories.analysis_run_repo import AnalysisRunRepository
    from repositories.snapshot_resolution_repo import SnapshotResolutionRepository

    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    async with get_database_manager().session() as session:
        report = await run_shadow_pipeline(
            session,
            connector_name="dummy",
            match_id="dummy-match-1",
            final_score={"home": 2, "away": 1},
            status="FINAL",
            now_utc=now,
        )
        assert "error" not in report or report.get("error") is None
        assert report.get("analysis", {}).get("snapshot_id") is not None
        snapshot_id = report["analysis"]["snapshot_id"]

        run_repo = AnalysisRunRepository(session)
        resolution_repo = SnapshotResolutionRepository(session)
        run = await run_repo.get_by_id(snapshot_id)
        assert run is not None
        assert run.match_id == "dummy-match-1"
        res = await resolution_repo.get_by_analysis_run_id(snapshot_id)
        assert res is not None
        assert res.final_home_goals == 2
        assert res.final_away_goals == 1


@pytest.mark.asyncio
async def test_shadow_pipeline_report_sections_populated(test_db):
    """PipelineReport has all sections populated."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    async with get_database_manager().session() as session:
        report = await run_shadow_pipeline(
            session,
            connector_name="dummy",
            match_id="dummy-match-2",
            final_score={"home": 1, "away": 1},
            status="FINAL",
            now_utc=now,
        )

    assert "ingestion" in report
    assert "payload_checksum" in report["ingestion"]
    assert report["ingestion"]["payload_checksum"] is not None
    assert "collected_at" in report["ingestion"]

    assert "analysis" in report
    assert "snapshot_id" in report["analysis"]
    assert "markets_picks_confidences" in report["analysis"]

    assert "resolution" in report
    assert "market_outcomes" in report["resolution"]

    assert "evaluation_report_checksum" in report
    assert report["evaluation_report_checksum"] is not None

    assert "proposal" in report
    assert "diffs" in report["proposal"]
    assert "guardrails_results" in report["proposal"]
    assert "proposal_checksum" in report["proposal"]

    assert "audit" in report
    assert "changed_count" in report["audit"]
    assert "per_market_change_count" in report["audit"]
    assert "snapshots_checksum" in report["audit"]
    assert "current_policy_checksum" in report["audit"]
    assert "proposed_policy_checksum" in report["audit"]


@pytest.mark.asyncio
async def test_shadow_pipeline_deterministic_same_checksums(test_db):
    """Running twice with same inputs and fixed now yields same checksums (use two fresh DBs)."""
    now = datetime(2025, 6, 1, 14, 0, 0, tzinfo=timezone.utc)

    async def run_once():
        await init_database("sqlite+aiosqlite:///:memory:")
        engine = get_database_manager().engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with get_database_manager().session() as session:
            report = await run_shadow_pipeline(
                session,
                connector_name="dummy",
                match_id="dummy-match-3",
                final_score={"home": 0, "away": 0},
                status="FINAL",
                now_utc=now,
            )
        await dispose_database()
        return report

    report1 = await run_once()
    report2 = await run_once()

    # payload_checksum can vary if pipeline includes timestamps in payload; other checksums are deterministic
    assert report1["evaluation_report_checksum"] == report2["evaluation_report_checksum"]
    assert report1["proposal"]["proposal_checksum"] == report2["proposal"]["proposal_checksum"]
    assert report1["audit"]["snapshots_checksum"] == report2["audit"]["snapshots_checksum"]
    assert report1["audit"]["current_policy_checksum"] == report2["audit"]["current_policy_checksum"]
    assert report1["audit"]["proposed_policy_checksum"] == report2["audit"]["proposed_policy_checksum"]
