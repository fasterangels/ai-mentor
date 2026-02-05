"""
Integration tests: injury/news resolver with DB (seed reports/claims, run resolver, assert resolutions).
Includes determinism: run twice, assert identical results and no duplicate rows.
"""

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
from models.injury_news_claim import InjuryNewsClaim
from models.injury_news_report import InjuryNewsReport
from repositories.injury_news_claim_repo import InjuryNewsClaimRepository
from repositories.injury_news_report_repo import InjuryNewsReportRepository
from repositories.injury_news_resolution_repo import InjuryNewsResolutionRepository
from ingestion.injury_news_resolver import run_injury_news_resolver


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


async def _seed_two_reports_conflicting_claims(session) -> None:
    """Seed 2 reports (different adapter_key) with conflicting claims for same team/player."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    report_repo = InjuryNewsReportRepository(session)
    claim_repo = InjuryNewsClaimRepository(session)

    await report_repo.upsert_report(
        report_id="rpt-a",
        adapter_key="recorded_injury_news_v1",
        artifact_path="reports/a.json",
        artifact_checksum="a1",
        content_checksum="c1",
        recorded_at=now,
        created_at=now,
        published_at=now,
    )
    await report_repo.upsert_report(
        report_id="rpt-b",
        adapter_key="recorded_injury_news_v1",
        artifact_path="reports/b.json",
        artifact_checksum="b1",
        content_checksum="c2",
        recorded_at=now,
        created_at=now,
        published_at=now,
    )
    await session.flush()

    await claim_repo.add_claims(
        report_id="rpt-a",
        claims=[
            {
                "team_ref": "team_x",
                "player_ref": "player_y",
                "claim_type": "INJURY_STATUS",
                "status": "OUT",
                "validity": "RANGE",
                "confidence": 0.9,
                "valid_from": now,
                "valid_to": datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc),
            },
        ],
        created_at=now,
    )
    await claim_repo.add_claims(
        report_id="rpt-b",
        claims=[
            {
                "team_ref": "team_x",
                "player_ref": "player_y",
                "claim_type": "INJURY_STATUS",
                "status": "FIT",
                "validity": "RANGE",
                "confidence": 0.9,
                "valid_from": now,
                "valid_to": datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc),
            },
        ],
        created_at=now,
    )
    await session.commit()


@pytest.mark.asyncio
async def test_resolver_integration_seed_run_assert(test_db) -> None:
    """Seed DB with 2 reports and conflicting claims; run resolver; assert resolutions row count and fields."""
    async with get_database_manager().session() as session:
        await _seed_two_reports_conflicting_claims(session)

    async with get_database_manager().session() as session:
        summary = await run_injury_news_resolver(
            session, policy_version="injury_news.v1", now_utc=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        await session.commit()

    assert summary["policy_version"] == "injury_news.v1"
    assert summary["resolutions_count"] >= 1
    assert "candidate_counts" in summary

    async with get_database_manager().session() as session:
        res_repo = InjuryNewsResolutionRepository(session)
        all_res = await res_repo.list_resolutions(limit=100)
        assert len(all_res) == summary["resolutions_count"]
        for r in all_res:
            assert r.team_ref
            assert r.resolved_status in ("AVAILABLE", "QUESTIONABLE", "OUT", "SUSPENDED", "UNKNOWN")
            assert r.policy_version == "injury_news.v1"
            # supporting_claim_ids and conflicting_claim_ids are JSON strings
            sup = json.loads(r.supporting_claim_ids) if r.supporting_claim_ids else []
            conf = json.loads(r.conflicting_claim_ids) if r.conflicting_claim_ids else []
            assert isinstance(sup, list)
            assert isinstance(conf, list)
            # Deterministic order (sorted in resolver)
            assert sup == sorted(sup) or sup == sorted(sup, key=int)
            assert conf == sorted(conf) or conf == sorted(conf, key=int)


@pytest.mark.asyncio
async def test_resolver_determinism_twice_same_result(test_db) -> None:
    """Run resolver twice on same DB and policy; assert identical resolutions and no duplicate rows."""
    async with get_database_manager().session() as session:
        await _seed_two_reports_conflicting_claims(session)

    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    async with get_database_manager().session() as session:
        summary1 = await run_injury_news_resolver(session, policy_version="injury_news.v1", now_utc=now)
        await session.commit()

    async with get_database_manager().session() as session:
        res_repo = InjuryNewsResolutionRepository(session)
        after_first = await res_repo.list_resolutions(limit=100)
        count_first = len(after_first)
        snap1 = [(r.team_ref, r.player_ref, r.resolved_status, r.supporting_claim_ids, r.conflicting_claim_ids) for r in after_first]

    async with get_database_manager().session() as session:
        summary2 = await run_injury_news_resolver(session, policy_version="injury_news.v1", now_utc=now)
        await session.commit()

    async with get_database_manager().session() as session:
        res_repo = InjuryNewsResolutionRepository(session)
        after_second = await res_repo.list_resolutions(limit=100)
        count_second = len(after_second)
        snap2 = [(r.team_ref, r.player_ref, r.resolved_status, r.supporting_claim_ids, r.conflicting_claim_ids) for r in after_second]

    assert summary1["resolutions_count"] == summary2["resolutions_count"]
    assert count_first == count_second, "second run should replace not append"
    assert snap1 == snap2, "resolutions must be identical after two runs (determinism)"
