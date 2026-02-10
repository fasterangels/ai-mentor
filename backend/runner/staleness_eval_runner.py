"""
Staleness evaluation runner (G4): run staleness metrics per reason only.
Measurement-only; no analyzer, no policy changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.staleness_metrics import run_staleness_evaluation


async def run_staleness_eval_mode(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    index_path: str | Path | None = None,
) -> Dict[str, Any]:
    """
    Run staleness evaluation: load evaluation data with evidence age, aggregate by (market, reason_code, age_band), write reports.
    """
    return await run_staleness_evaluation(
        session,
        reports_dir=reports_dir,
        index_path=index_path,
    )
