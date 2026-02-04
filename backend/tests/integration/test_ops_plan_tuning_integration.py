"""
Integration test: ops plan-tuning over small seeded history.
Asserts: plan produced, replay regression executed, and plan blocked when thresholds exceeded (synthetic case).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

import models  # noqa: F401
from core.database import dispose_database, get_database_manager, init_database
from models.base import Base
from offline_eval.decision_quality import compute_decision_quality_report
from runner.tuning_plan_runner import run_plan_tuning


def _record(run_id: int, created: str, match_id: str, outcomes: dict, predictions: list) -> dict:
    return {
        "run_id": run_id,
        "created_at_utc": created,
        "match_id": match_id,
        "market_outcomes": outcomes,
        "reason_codes_by_market": {},
        "predictions": predictions,
    }


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
async def test_plan_tuning_produces_plan_and_runs_replay(test_db, tmp_path) -> None:
    """Run plan-tuning over small seeded history; assert plan produced and replay_regression executed."""
    records = [
        _record(1, "2025-01-01T12:00:00+00:00", "m1", {"one_x_two": "SUCCESS", "over_under_25": "SUCCESS", "gg_ng": "FAILURE"}, [
            {"market": "1X2", "pick": "home", "confidence": 0.65},
            {"market": "OU25", "pick": "over", "confidence": 0.63},
            {"market": "GGNG", "pick": "yes", "confidence": 0.70},
        ]),
        _record(2, "2025-01-02T12:00:00+00:00", "m1", {"one_x_two": "FAILURE", "over_under_25": "SUCCESS", "gg_ng": "SUCCESS"}, [
            {"market": "1X2", "pick": "away", "confidence": 0.62},
            {"market": "OU25", "pick": "under", "confidence": 0.68},
            {"market": "GGNG", "pick": "no", "confidence": 0.65},
        ]),
    ]
    quality_audit = compute_decision_quality_report(records)
    reports_dir = tmp_path / "reports"
    index_path = reports_dir / "index.json"
    reports_dir.mkdir(parents=True, exist_ok=True)

    async with get_database_manager().session() as session:
        result = await run_plan_tuning(
            session,
            quality_audit_report=quality_audit,
            records=records,
            dry_run=True,
            reports_dir=str(reports_dir),
            index_path=str(index_path),
        )

    assert "plan" in result
    assert "replay_regression" in result
    assert result.get("proposal_count") is not None
    assert "run_count" in result
    assert result["run_count"] == len(records)
    assert "status" in result
    assert result["status"] in ("PASS", "FAIL")
    assert "reasons" in result
    assert "run_id" in result


@pytest.mark.asyncio
async def test_plan_tuning_blocked_when_coverage_drop_exceeds_threshold(test_db, tmp_path) -> None:
    """Synthetic case: records all at min confidence; plan raises one_x_two bar -> replay coverage drop blocks."""
    # All predictions at 0.62 so baseline covers everything. Audit suggests raising one_x_two to 0.67.
    records = [
        _record(
            i,
            f"2025-01-{i:02d}T12:00:00+00:00",
            "m1",
            {"one_x_two": "SUCCESS", "over_under_25": "SUCCESS", "gg_ng": "SUCCESS"},
            [
                {"market": "1X2", "pick": "home", "confidence": 0.62},
                {"market": "OU25", "pick": "over", "confidence": 0.62},
                {"market": "GGNG", "pick": "yes", "confidence": 0.62},
            ],
        )
        for i in range(1, 11)
    ]
    quality_audit = {
        "summary": {"run_count": len(records)},
        "suggestions": {
            "confidence_band_adjustments": [
                {
                    "market": "one_x_two",
                    "band": "0.60-0.65",
                    "predicted_confidence": 0.625,
                    "empirical_accuracy": 0.40,
                    "deviation": 0.225,
                    "count": 20,
                    "suggestion": "consider shifting band",
                },
            ],
            "dampening_candidates": [],
        },
        "confidence_calibration": {},
    }
    reports_dir = tmp_path / "reports"
    index_path = reports_dir / "index.json"
    reports_dir.mkdir(parents=True, exist_ok=True)

    async with get_database_manager().session() as session:
        result = await run_plan_tuning(
            session,
            quality_audit_report=quality_audit,
            records=records,
            dry_run=True,
            reports_dir=str(reports_dir),
            index_path=str(index_path),
        )

    replay = result.get("replay_regression") or {}
    # Proposed one_x_two min_confidence will be 0.67 (0.62 + 0.05 cap). All our one_x_two preds are 0.62, so they get excluded -> coverage drop
    assert replay.get("blocked") is True, "replay should block when proposed min_confidence excludes most predictions"
    assert result.get("status") == "FAIL"
    assert any("coverage_drop" in r for r in (result.get("reasons") or [])), "reasons should mention coverage_drop"
