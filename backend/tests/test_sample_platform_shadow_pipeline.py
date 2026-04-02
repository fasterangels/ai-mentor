"""
E2E: full shadow pipeline with connector sample_platform; report sections and deterministic checksums.
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

import models  # noqa: F401
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
async def test_shadow_pipeline_sample_platform_produces_full_report(test_db) -> None:
    """Full shadow pipeline runs using sample_platform and produces PipelineReport with all sections."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    async with get_database_manager().session() as session:
        report = await run_shadow_pipeline(
            session,
            connector_name="sample_platform",
            match_id="sample_platform_match_001",
            final_score={"home": 2, "away": 1},
            status="FINAL",
            now_utc=now,
        )

    assert report.get("error") is None
    assert "ingestion" in report
    assert report["ingestion"].get("payload_checksum") is not None
    assert "analysis" in report
    assert "markets_picks_confidences" in report["analysis"]
    assert "resolution" in report
    assert "market_outcomes" in report["resolution"]
    assert "evaluation_report_checksum" in report
    assert report["evaluation_report_checksum"] is not None
    assert "proposal" in report
    assert "proposal_checksum" in report["proposal"]
    assert "tuner_proposal_diff" in report
    assert "policy_from_version" in report["tuner_proposal_diff"]
    assert "top_changes" in report["tuner_proposal_diff"]
    assert "tuner_impact_by_market" in report
    assert list(report["tuner_impact_by_market"].keys()) == ["one_x_two", "over_under_25", "gg_ng"]
    assert "audit" in report
    assert "changed_count" in report["audit"]
    assert "snapshots_checksum" in report["audit"]


@pytest.mark.asyncio
async def test_shadow_pipeline_sample_platform_deterministic_checksums(test_db) -> None:
    """Same inputs + fixed now_utc yield same checksums (two independent runs)."""
    now = datetime(2025, 7, 1, 10, 0, 0, tzinfo=timezone.utc)

    async def run_once():
        await init_database("sqlite+aiosqlite:///:memory:")
        engine = get_database_manager().engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with get_database_manager().session() as session:
            report = await run_shadow_pipeline(
                session,
                connector_name="sample_platform",
                match_id="sample_platform_match_002",
                final_score={"home": 0, "away": 0},
                status="FINAL",
                now_utc=now,
            )
        await dispose_database()
        return report

    report1 = await run_once()
    report2 = await run_once()

    assert report1.get("error") is None and report2.get("error") is None
    assert report1["ingestion"]["payload_checksum"] == report2["ingestion"]["payload_checksum"]
    assert report1["evaluation_report_checksum"] == report2["evaluation_report_checksum"]
    assert report1["proposal"]["proposal_checksum"] == report2["proposal"]["proposal_checksum"]
    assert report1["audit"]["snapshots_checksum"] == report2["audit"]["snapshots_checksum"]
