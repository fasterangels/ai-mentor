"""
Delta evaluation runner (G3): run live vs recorded delta evaluation only.
Measurement-only; no analyzer, no decisions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.live_recorded_delta import run_delta_evaluation


async def run_delta_eval_mode(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    index_path: str | Path | None = None,
) -> Dict[str, Any]:
    """
    Run delta evaluation: load recorded + live_shadow snapshots, compute deltas, write report.
    """
    return await run_delta_evaluation(
        session,
        reports_dir=reports_dir,
        index_path=index_path,
    )
