"""
Worst-case tracking run mode: compute worst-case report from stored evaluation data,
write worst_case_errors_top.csv and worst_case_errors_top.json. Measurement-only; no enforcement.
Must NOT run by default; invoked explicitly via --ops worst-case-tracking (or --mode worst-case-tracking).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.worst_case_errors import (
    EvaluatedDecision,
    compute_worst_case_report,
)
from evaluation.worst_case_errors.reporting import (
    DEFAULT_TOP_N,
    write_csv,
    write_json,
)
from ops.ops_events import (
    log_worst_case_end,
    log_worst_case_missing_inputs,
    log_worst_case_start,
    log_worst_case_written,
)

MODE_WORST_CASE_TRACKING = "worst-case-tracking"
MARKETS = ("one_x_two", "over_under_25", "gg_ng")
MARKET_KEY_MAP = {
    "1X2": "one_x_two",
    "OU25": "over_under_25",
    "OU_2.5": "over_under_25",
    "GGNG": "gg_ng",
    "BTTS": "gg_ng",
}
LIVE_SHADOW_MODE = "LIVE_SHADOW_ANALYZE"

CSV_FILENAME = "worst_case_errors_top.csv"
JSON_FILENAME = "worst_case_errors_top.json"


def _snapshot_type_from_run_mode(mode: Optional[str]) -> str:
    """Map analysis run mode to snapshot_type for reporting."""
    if mode == LIVE_SHADOW_MODE:
        return "live_shadow"
    return "recorded"


async def load_decisions_from_session(
    session: AsyncSession,
    from_utc: Optional[datetime] = None,
    to_utc: Optional[datetime] = None,
    limit: int = 5000,
) -> List[EvaluatedDecision]:
    """
    Load resolved analysis runs + resolutions + predictions and convert to EvaluatedDecision list.
    Uses only stored data; no live IO.
    """
    from repositories.analysis_run_repo import AnalysisRunRepository
    from repositories.snapshot_resolution_repo import SnapshotResolutionRepository
    from repositories.prediction_repo import PredictionRepository

    run_repo = AnalysisRunRepository(session)
    resolution_repo = SnapshotResolutionRepository(session)
    pred_repo = PredictionRepository(session)

    runs = await run_repo.list_by_created_between(from_utc=from_utc, to_utc=to_utc, limit=limit)
    decisions: List[EvaluatedDecision] = []

    for run in runs:
        res = await resolution_repo.get_by_analysis_run_id(run.id)
        if res is None:
            continue
        try:
            mo = json.loads(res.market_outcomes_json) if isinstance(res.market_outcomes_json, str) else (res.market_outcomes_json or {})
        except (TypeError, ValueError):
            mo = {}
        preds = await pred_repo.list_by_analysis_run(run.id)
        match_id = res.match_id or ""
        run_mode = getattr(run, "mode", None)
        snapshot_type = _snapshot_type_from_run_mode(run_mode)
        snapshot_ids = [str(run.id)]

        for p in preds:
            raw_market = (p.market or "").strip().upper()
            market = MARKET_KEY_MAP.get(raw_market) or MARKET_KEY_MAP.get((p.market or "").strip(), "")
            if not market or market not in MARKETS:
                continue
            outcome = mo.get(market, "UNRESOLVED")
            confidence = getattr(p, "confidence", None)
            if confidence is None:
                confidence = 0.0
            else:
                try:
                    confidence = max(0.0, min(1.0, float(confidence)))
                except (TypeError, ValueError):
                    confidence = 0.0
            pick = (p.pick or "").strip() or ""
            decisions.append(
                EvaluatedDecision(
                    fixture_id=match_id,
                    market=market,
                    prediction=pick,
                    outcome=outcome,
                    original_confidence=confidence,
                    uncertainty_shadow=None,
                    snapshot_ids=snapshot_ids,
                    snapshot_type=snapshot_type,
                )
            )

    return decisions


async def run_worst_case_tracking(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    top_n: int = DEFAULT_TOP_N,
    from_utc: Optional[datetime] = None,
    to_utc: Optional[datetime] = None,
    limit: int = 5000,
) -> dict[str, Any]:
    """
    Load decisions from DB, compute worst-case report, write CSV and JSON.
    Returns summary dict (error, decisions_count, csv_path, json_path, rows_written).
    """
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    csv_path = reports_path / CSV_FILENAME
    json_path = reports_path / JSON_FILENAME

    log_worst_case_start(str(reports_path))
    t0 = time.perf_counter()

    decisions = await load_decisions_from_session(session, from_utc=from_utc, to_utc=to_utc, limit=limit)

    if not decisions:
        log_worst_case_missing_inputs("no resolved evaluation data (zero decisions)")
        report = compute_worst_case_report([], top_n=None, computed_at_utc=datetime.now(timezone.utc))
        write_csv(report, csv_path, top_n=top_n)
        write_json(report, json_path, top_n=top_n)
        log_worst_case_written(str(csv_path), str(json_path), 0)
        log_worst_case_end(str(reports_path), duration_seconds=time.perf_counter() - t0, decisions_count=0, rows_written=0)
        return {
            "error": None,
            "detail": "no resolved evaluation data",
            "decisions_count": 0,
            "csv_path": str(csv_path),
            "json_path": str(json_path),
            "rows_written": 0,
        }

    report = compute_worst_case_report(decisions, top_n=None, computed_at_utc=datetime.now(timezone.utc))
    write_csv(report, csv_path, top_n=top_n)
    write_json(report, json_path, top_n=top_n)
    rows_written = min(top_n, len(report.rows))

    log_worst_case_written(str(csv_path), str(json_path), rows_written)
    log_worst_case_end(
        str(reports_path),
        duration_seconds=time.perf_counter() - t0,
        decisions_count=len(decisions),
        rows_written=rows_written,
    )

    return {
        "error": None,
        "decisions_count": len(decisions),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "rows_written": rows_written,
        "computed_at_utc": report.computed_at_utc.isoformat(),
    }
