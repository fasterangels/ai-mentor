"""
Integration tests for snapshot replay wiring in POST /api/v1/pipeline/shadow/run.
Default mode unchanged; when SNAPSHOT_REPLAY_ENABLED=true, runs replay_from_snapshots only.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import models  # noqa: F401
import pytest
from fastapi.testclient import TestClient

from core.database import dispose_database, get_database_manager, init_database
from main import app
from models.base import Base


@pytest.fixture
def test_db():
    """In-memory SQLite so pipeline/shadow/run dependency get_db_session succeeds."""
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


def test_pipeline_shadow_run_default_mode_no_snapshot_replay(test_db) -> None:
    """A) Default mode: flags unset -> response does not include snapshot_replay mode."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("SNAPSHOT_REPLAY_ENABLED", raising=False)
        m.delenv("SNAPSHOT_REPLAY_DIR", raising=False)
        client = TestClient(app)
        resp = client.post("/api/v1/pipeline/shadow/run", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("error") == "MISSING_MATCH_ID"
    assert data.get("mode") != "snapshot_replay"
    assert "snapshot_replay" not in data or data.get("snapshot_replay") is None


def test_pipeline_shadow_run_replay_mode_returns_report(test_db) -> None:
    """B) Replay mode: SNAPSHOT_REPLAY_ENABLED=true and dir with stub JSON -> 200 and mode snapshot_replay."""
    base = Path("reports/snapshots").resolve()
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / "replay_c8_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stub1.json").write_text(
        json.dumps({"note": "stub", "run_id": "replay_c8_run", "filename": "stub1.json"}),
        encoding="utf-8",
    )
    try:
        with pytest.MonkeyPatch.context() as m:
            m.setenv("SNAPSHOT_REPLAY_ENABLED", "true")
            m.setenv("SNAPSHOT_REPLAY_DIR", str(run_dir))
            client = TestClient(app)
            resp = client.post("/api/v1/pipeline/shadow/run", json={"match_id": "any"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("mode") == "snapshot_replay"
        assert "snapshot_replay" in data
        assert data["snapshot_replay"].get("snapshots_used") == 1
        assert "report_path" in data["snapshot_replay"]
    finally:
        replay_report = run_dir / "replay_report.json"
        if replay_report.exists():
            replay_report.unlink()
        if (run_dir / "stub1.json").exists():
            (run_dir / "stub1.json").unlink()
        try:
            run_dir.rmdir()
        except OSError:
            pass
