"""POST /api/v1/pipeline/shadow/run — run shadow pipeline (read-only; no policy apply)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from pipeline.shadow_pipeline import run_shadow_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _replay_report(replay_result: dict) -> dict:
    """Build a PipelineReport-shaped dict for snapshot replay mode."""
    return {
        "mode": "snapshot_replay",
        "ingestion": {"payload_checksum": None, "collected_at": None},
        "analysis": {"snapshot_id": None, "markets_picks_confidences": {}},
        "resolution": {"market_outcomes": {}},
        "evaluation_report_checksum": None,
        "proposal": {"diffs": [], "guardrails_results": [], "proposal_checksum": None},
        "audit": {"changed_count": 0, "per_market_change_count": {}, "snapshots_checksum": None, "current_policy_checksum": None, "proposed_policy_checksum": None},
        "snapshot_replay": {
            "snapshots_used": replay_result.get("snapshots_used", 0),
            "report_path": replay_result.get("report_path", ""),
            "note": replay_result.get("note", "recorded replay"),
        },
    }


@router.post(
    "/shadow/run",
    summary="Run shadow pipeline",
    response_description="PipelineReport (ingestion, analysis, resolution, evaluation checksum, proposal, audit). Does NOT apply policy.",
)
async def shadow_run(
    body: dict,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Run end-to-end shadow pipeline: ingestion -> analysis -> result attach -> evaluation -> tune -> audit.
    Body: connector_name (default dummy), match_id, final_home_goals, final_away_goals, status (default FINAL).
    When SNAPSHOT_REPLAY_ENABLED=true and SNAPSHOT_REPLAY_DIR set, runs replay-from-snapshots only (no live ingestion).
    Returns PipelineReport. Does NOT apply any policy automatically.
    """
    snapshot_replay_enabled = os.environ.get("SNAPSHOT_REPLAY_ENABLED", "").strip().lower() == "true"
    if snapshot_replay_enabled:
        snapshot_replay_dir = os.environ.get("SNAPSHOT_REPLAY_DIR", "").strip()
        if not snapshot_replay_dir:
            return {
                "error": "SNAPSHOT_REPLAY_DIR_REQUIRED",
                "detail": "SNAPSHOT_REPLAY_DIR is required when SNAPSHOT_REPLAY_ENABLED is true",
                "ingestion": {},
                "analysis": {},
                "resolution": {},
                "evaluation_report_checksum": None,
                "proposal": {},
                "audit": {},
            }
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        src_dir = repo_root / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        from ai_mentor.live_snapshot.replay import replay_from_snapshots
        replay_result = replay_from_snapshots(snapshot_replay_dir)
        report = _replay_report(replay_result)
        return report

    connector_name = (body.get("connector_name") or "dummy").strip()
    match_id = (body.get("match_id") or "").strip()
    if not match_id:
        return {
            "error": "MISSING_MATCH_ID",
            "detail": "match_id is required",
            "ingestion": {},
            "analysis": {},
            "resolution": {},
            "evaluation_report_checksum": None,
            "proposal": {},
            "audit": {},
        }
    final_home_goals = int(body.get("final_home_goals", 0))
    final_away_goals = int(body.get("final_away_goals", 0))
    status = (body.get("status") or "FINAL").strip()
    report = await run_shadow_pipeline(
        session,
        connector_name=connector_name,
        match_id=match_id,
        final_score={"home": final_home_goals, "away": final_away_goals},
        status=status,
    )
    await session.commit()
    return report
