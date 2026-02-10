"""Contract validation gate: report.v1 schema and backward-compatibility snapshot."""
from __future__ import annotations
import json
import sys
from pathlib import Path
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
import jsonschema

REQUIRED_TOP_LEVEL = ("schema_version", "canonical_flow", "generated_at", "ingestion", "analysis", "resolution", "evaluation_report_checksum", "proposal", "audit")

def _schema_path():
    return _backend / "contracts" / "report.v1.schema.json"

def _sample_path():
    return Path(__file__).resolve().parent / "fixtures" / "contracts" / "report.v1.sample.json"

def test_report_v1_sample_passes_schema():
    with open(_schema_path(), encoding="utf-8-sig") as f:
        schema = json.load(f)
    with open(_sample_path(), encoding="utf-8-sig") as f:
        sample = json.load(f)
    jsonschema.validate(instance=sample, schema=schema)

def test_report_has_required_fields_snapshot_stability():
    with open(_sample_path(), encoding="utf-8-sig") as f:
        sample = json.load(f)
    for key in REQUIRED_TOP_LEVEL:
        assert key in sample, f"Required key {key!r} missing from contract sample"
    assert sample.get("schema_version") == "report.v1"
    assert sample.get("canonical_flow") == "/pipeline/shadow/run"


@pytest.fixture
def test_db():
    import asyncio
    import models  # noqa: F401
    from core.database import init_database, dispose_database, get_database_manager
    from models.base import Base
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
async def test_pipeline_report_validates_against_report_v1_schema(test_db):
    """Run pipeline on fixed fixture and validate response against report.v1.schema.json."""
    from datetime import datetime, timezone
    from core.database import get_database_manager
    from pipeline.shadow_pipeline import run_shadow_pipeline
    async with get_database_manager().session() as session:
        report = await run_shadow_pipeline(
            session,
            connector_name="sample_platform",
            match_id="sample_platform_match_001",
            final_score={"home": 2, "away": 1},
            status="FINAL",
            now_utc=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
    with open(_schema_path(), encoding="utf-8-sig") as f:
        schema = json.load(f)
    jsonschema.validate(instance=report, schema=schema)
    for key in REQUIRED_TOP_LEVEL:
        assert key in report, f"Pipeline report missing required key {key!r}"
