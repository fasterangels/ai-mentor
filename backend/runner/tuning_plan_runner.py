"""
Tuning plan workflow: quality_audit -> tuning_planner -> replay regression (shadow-only).
Writes reports/tuning_plan/<run_id>.json and index entry. Blocks if coverage/accuracy thresholds exceeded.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from offline_eval.decision_quality import compute_decision_quality_report, load_history_from_session
from policy.tuning_planner import plan_from_quality_audit, replay_regression
from reports.index_store import append_tuning_plan_run, load_index, save_index

TUNING_PLAN_SUBDIR = "tuning_plan"
INDEX_PATH = "reports/index.json"
COVERAGE_DROP_THRESHOLD = 0.10
ACCURACY_DROP_THRESHOLD = 0.05


def _run_id() -> str:
    return f"tuning_plan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


async def run_plan_tuning(
    session: AsyncSession,
    *,
    last_n: int = 500,
    quality_audit_report: Optional[Dict[str, Any]] = None,
    records: Optional[List[Dict[str, Any]]] = None,
    dry_run: bool = False,
    reports_dir: str | Path = "reports",
    index_path: str | Path = INDEX_PATH,
) -> Dict[str, Any]:
    """
    Run: (quality_audit if missing) -> plan_from_quality_audit -> replay_regression.
    If replay blocked (coverage drop > 10% or accuracy drop > threshold), status FAIL and plan not applied.
    Writes report to reports/tuning_plan/<run_id>.json and appends to index.
    """
    run_id = _run_id()
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
    reports_path = Path(reports_dir)

    if records is None:
        records = await load_history_from_session(session, limit=last_n)
    if quality_audit_report is None:
        quality_audit_report = compute_decision_quality_report(records)

    plan = plan_from_quality_audit(quality_audit_report)
    proposals = plan.get("proposals") or []
    proposed_snapshot = plan.get("proposed_policy_snapshot") or {}
    markets_snapshot = proposed_snapshot.get("markets") or {}
    proposed_min_confidence = {m: markets_snapshot.get(m, {}).get("min_confidence", 0.62) for m in ("one_x_two", "over_under_25", "gg_ng")}

    replay = replay_regression(
        records,
        proposed_min_confidence,
        coverage_drop_threshold=COVERAGE_DROP_THRESHOLD,
        accuracy_drop_threshold=ACCURACY_DROP_THRESHOLD,
    )
    blocked = replay.get("blocked", False)
    status = "FAIL" if blocked else "PASS"
    reasons = replay.get("reasons") or []

    payload = {
        "run_id": run_id,
        "created_at_utc": created_at,
        "status": status,
        "blocked": blocked,
        "reasons": reasons,
        "plan": plan,
        "replay_regression": replay,
        "proposal_count": len(proposals),
        "run_count": len(records),
    }

    if not dry_run:
        out_dir = reports_path / TUNING_PLAN_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)
        report_file = out_dir / f"{run_id}.json"
        report_file.write_text(_stable_json(payload), encoding="utf-8")

        index = load_index(index_path)
        append_tuning_plan_run(index, {
            "run_id": run_id,
            "created_at_utc": created_at,
            "status": status,
            "proposal_count": len(proposals),
            "blocked": blocked,
            "reasons": reasons,
        })
        save_index(index, index_path)
        payload["_report_path"] = str(report_file)

    return payload
