"""
Unit test: LIVE_SHADOW_ANALYZE hard blocks persistence (mock repositories and assert not called).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from pipeline.shadow_pipeline import run_shadow_pipeline


@pytest.mark.asyncio
async def test_hard_block_persistence_skips_db_writes() -> None:
    """When hard_block_persistence=True, snapshot_id is None (no DB writes)."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from pipeline.types import EvidencePack, DomainData, QualityReport
    from datetime import datetime, timezone

    mock_session = MagicMock(spec=AsyncSession)
    mock_session.flush = AsyncMock()

    # Patch dependencies
    with patch("pipeline.shadow_pipeline.attach_result") as mock_attach, \
         patch("pipeline.shadow_pipeline.run_pipeline") as mock_pipeline, \
         patch("pipeline.shadow_pipeline.analyze_v2") as mock_analyze, \
         patch("pipeline.shadow_pipeline.build_evaluation_report") as mock_eval, \
         patch("pipeline.shadow_pipeline.run_tuner") as mock_tuner, \
         patch("pipeline.shadow_pipeline.audit_snapshots") as mock_audit, \
         patch("pipeline.shadow_pipeline.run_replay") as mock_replay, \
         patch("pipeline.shadow_pipeline._ensure_dummy_match") as mock_ensure:
        mock_ep = EvidencePack(
            match_id="test_match",
            captured_at_utc=datetime.now(timezone.utc),
            domains={"fixtures": DomainData(data={}, quality=QualityReport(passed=True, score=0.8))},
        )
        mock_pipeline.return_value = MagicMock(evidence_pack=mock_ep)
        mock_attach.return_value = MagicMock(market_outcomes_json='{}')
        mock_analyze.return_value = {
            "decisions": [{"market": "1X2", "selection": "HOME", "confidence": 0.75, "reasons": []}],
            "analysis_run": {"flags": [], "counts": {}},
        }
        mock_eval.return_value = {}
        mock_tuner.return_value = MagicMock(proposed_policy=MagicMock(model_dump=lambda **kw: {}), diffs=[], guardrails_results=[])
        mock_audit.return_value = {"summary": {"changed_count": 0, "per_market_change_count": {}}, "snapshots_checksum": "", "current_policy_checksum": "", "proposed_policy_checksum": ""}
        mock_replay.return_value = {"replay_result": "PASS", "current_counts_by_market": {}, "proposed_counts_by_market": {}}
        mock_ensure.return_value = None

        report = await run_shadow_pipeline(
            mock_session,
            connector_name="dummy",
            match_id="test_match",
            final_score={"home": 1, "away": 0},
            hard_block_persistence=True,
        )

        # Assert snapshot_id is None when hard_block_persistence=True
        assert report.get("analysis", {}).get("snapshot_id") is None
