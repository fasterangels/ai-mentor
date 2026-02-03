"""Tests for POST /api/v1/results/attach — attach final result and persist outcomes."""

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
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import init_database, dispose_database, get_database_manager
from main import app
from models.base import Base
from models.analysis_run import AnalysisRun
from models.competition import Competition
from models.match import Match
from models.prediction import Prediction
from models.season import Season
from models.team import Team
from repositories.analysis_run_repo import AnalysisRunRepository
from repositories.prediction_repo import PredictionRepository
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository


@pytest.fixture
def test_db():
    """Use in-memory SQLite for tests (sync fixture runs async setup/teardown)."""
    async def _setup():
        url = "sqlite+aiosqlite:///:memory:"
        await init_database(url)
        engine = get_database_manager().engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        await dispose_database()

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


async def _create_snapshot_with_predictions(session: AsyncSession) -> int:
    """Create minimal FK entities and one analysis run with three predictions."""
    now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    # Minimal FK chain: Competition, Season, Team x2, Match (commit parents first so FK succeed)
    comp = Competition(id="comp-1", name="Test", country="XX", tier=1, is_active=True)
    session.add(comp)
    season = Season(
        id="season-1", competition_id="comp-1", name="2024",
        year_start=2024, year_end=2025, is_active=True
    )
    session.add(season)
    t1 = Team(id="team-1", name="Home", country="XX", is_active=True)
    t2 = Team(id="team-2", name="Away", country="XX", is_active=True)
    session.add(t1)
    session.add(t2)
    await session.flush()
    match = Match(
        id="match-1",
        competition_id="comp-1",
        season_id="season-1",
        kickoff_utc=now,
        status="SCHEDULED",
        home_team_id="team-1",
        away_team_id="team-2",
    )
    session.add(match)
    await session.flush()

    run = AnalysisRun(
        created_at_utc=now,
        logic_version="test",
        mode="PREGAME",
        match_id="match-1",
        data_quality_score=0.9,
        flags_json="[]",
    )
    session.add(run)
    await session.flush()
    run_id = run.id
    assert run_id is not None

    for market, decision, pick, reasons in [
        ("1X2", "HOME", "HOME", ["reason_1x2_a"]),
        ("OU25", "OVER", "OVER", ["reason_ou_a"]),
        ("GGNG", "GG", "GG", ["reason_gg_a"]),
    ]:
        p = Prediction(
            created_at_utc=now,
            analysis_run_id=run_id,
            match_id="match-1",
            market=market,
            decision=decision,
            pick=pick,
            probabilities_json="{}",
            separation=0.1,
            confidence=0.65,
            risk=0.1,
            reasons_json=json.dumps(reasons),
            evidence_pack_json="{}",
        )
        session.add(p)
    await session.commit()
    return run_id


async def _create_snapshot_with_empty_reasons(session: AsyncSession) -> int:
    """Create one analysis run and three predictions with empty/null-like reasons_json (null-safety test)."""
    now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    comp = Competition(id="comp-2", name="Test2", country="XX", tier=1, is_active=True)
    session.add(comp)
    season = Season(
        id="season-2", competition_id="comp-2", name="2024",
        year_start=2024, year_end=2025, is_active=True
    )
    session.add(season)
    t1 = Team(id="team-3", name="Home2", country="XX", is_active=True)
    t2 = Team(id="team-4", name="Away2", country="XX", is_active=True)
    session.add(t1)
    session.add(t2)
    await session.flush()
    match = Match(
        id="match-2",
        competition_id="comp-2",
        season_id="season-2",
        kickoff_utc=now,
        status="SCHEDULED",
        home_team_id="team-3",
        away_team_id="team-4",
    )
    session.add(match)
    await session.flush()

    run = AnalysisRun(
        created_at_utc=now,
        logic_version="test",
        mode="PREGAME",
        match_id="match-2",
        data_quality_score=0.9,
        flags_json="[]",
    )
    session.add(run)
    await session.flush()
    run_id = run.id
    assert run_id is not None

    for market, decision, pick, reasons_json in [
        ("1X2", "HOME", "HOME", "[]"),
        ("OU25", "OVER", "OVER", ""),
        ("GGNG", "GG", "GG", "[]"),
    ]:
        p = Prediction(
            created_at_utc=now,
            analysis_run_id=run_id,
            match_id="match-2",
            market=market,
            decision=decision,
            pick=pick,
            probabilities_json="{}",
            separation=0.1,
            confidence=0.65,
            risk=0.1,
            reasons_json=reasons_json,
            evidence_pack_json="{}",
        )
        session.add(p)
    await session.commit()
    return run_id


@pytest.mark.asyncio
async def test_attach_result_persists_outcomes(test_db):
    """Endpoint attaches result and persists market outcomes."""
    from core.dependencies import get_db_session

    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session

    async with get_database_manager().session() as session:
        run_id = await _create_snapshot_with_predictions(session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post(
            "/api/v1/results/attach",
            json={
                "snapshot_id": str(run_id),
                "home_goals": 2,
                "away_goals": 1,
                "status": "FINAL",
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["snapshot_id"] == str(run_id)
    assert data["final_result"]["home_goals"] == 2 and data["final_result"]["away_goals"] == 1
    assert data["market_outcomes"]["one_x_two"] == "SUCCESS"
    assert data["market_outcomes"]["over_under_25"] == "SUCCESS"
    assert data["market_outcomes"]["gg_ng"] == "SUCCESS"

    async with get_database_manager().session() as session:
        res_repo = SnapshotResolutionRepository(session)
        res = await res_repo.get_by_analysis_run_id(run_id)
        assert res is not None
        assert res.home_goals == 2 and res.away_goals == 1
        mo = json.loads(res.market_outcomes_json)
        assert mo["one_x_two"] == "SUCCESS"

    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_attach_validation_goals_negative(test_db):
    """Attach with negative goals returns 422."""
    from core.dependencies import get_db_session

    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post(
            "/api/v1/results/attach",
            json={
                "snapshot_id": "1",
                "home_goals": -1,
                "away_goals": 0,
                "status": "FINAL",
            },
        )
    assert r.status_code == 422
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_attach_snapshot_not_found(test_db):
    """Attach with non-existent snapshot_id returns 404."""
    from core.dependencies import get_db_session

    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post(
            "/api/v1/results/attach",
            json={
                "snapshot_id": "99999",
                "home_goals": 0,
                "away_goals": 0,
                "status": "FINAL",
            },
        )
    assert r.status_code == 404
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_attach_with_empty_reasons_does_not_raise(test_db):
    """Attach with missing/empty reasons_json yields empty reason_codes_by_market; never raises."""
    from core.dependencies import get_db_session

    async def override_session():
        async with get_database_manager().session() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_session

    async with get_database_manager().session() as session:
        run_id = await _create_snapshot_with_empty_reasons(session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post(
            "/api/v1/results/attach",
            json={
                "snapshot_id": str(run_id),
                "home_goals": 1,
                "away_goals": 1,
                "status": "FINAL",
            },
        )
    assert r.status_code == 200

    async with get_database_manager().session() as session:
        res_repo = SnapshotResolutionRepository(session)
        res = await res_repo.get_by_analysis_run_id(run_id)
        assert res is not None
        rc = json.loads(res.reason_codes_by_market_json)
        assert rc["one_x_two"] == []
        assert rc["over_under_25"] == []
        assert rc["gg_ng"] == []

    app.dependency_overrides.pop(get_db_session, None)
