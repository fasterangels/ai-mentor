"""
Uncertainty escalation shadow (H3 Part B). Simulation only; NO refusals enforced.
Computes would_refuse per decision from uncertainty signals; writes reports only.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.staleness_metrics import _load_evaluation_data_with_evidence_age
from modeling.uncertainty import compute_uncertainty_profile, compute_would_refuse
from modeling.reason_decay.model import DecayModelParams, params_from_dict

REPORT_SUBDIR = "uncertainty_shadow"
CSV_NAME = "uncertainty_shadow.csv"
JSON_NAME = "uncertainty_shadow.json"
DECAY_PARAMS_JSON = "decay_fit/reason_decay_params.json"
PENALTY_SHADOW_JSON = "confidence_penalty_shadow/confidence_penalty_shadow.json"


def _load_decay_params_map(reports_dir: str | Path) -> Dict[Tuple[str, str], DecayModelParams]:
    """Load reason_decay_params.json. Deterministic."""
    path = Path(reports_dir) / DECAY_PARAMS_JSON
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    params_list = data.get("params")
    if not isinstance(params_list, list):
        return {}
    out: Dict[Tuple[str, str], DecayModelParams] = {}
    for p in params_list:
        if not isinstance(p, dict):
            continue
        params = params_from_dict(p)
        out[(params.market, params.reason_code)] = params
    return out


def _load_penalty_shadow_rows(reports_dir: str | Path) -> List[Dict[str, Any]]:
    """Load confidence penalty shadow rows from JSON. Deterministic."""
    path = Path(reports_dir) / PENALTY_SHADOW_JSON
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    rows = data.get("rows")
    if not isinstance(rows, list):
        return []
    return list(rows)


async def run_uncertainty_shadow(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    from_utc: Any = None,
    to_utc: Any = None,
    limit: int = 5000,
) -> Dict[str, Any]:
    """
    For each decision: compute uncertainty profile (Part A), compute would_refuse (simulation).
    Write uncertainty_shadow.csv and .json. No refusals enforced; reporting only.
    """
    from ops.ops_events import (
        log_uncertainty_shadow_end,
        log_uncertainty_shadow_start,
        log_uncertainty_shadow_written,
    )

    t_start = log_uncertainty_shadow_start()
    reports_dir = Path(reports_dir)
    out_dir = reports_dir / REPORT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)

    decay_params_map = _load_decay_params_map(reports_dir)
    shadow_rows = _load_penalty_shadow_rows(reports_dir)
    records, _ = await _load_evaluation_data_with_evidence_age(
        session, from_utc=from_utc, to_utc=to_utc, limit=limit
    )

    results: List[Dict[str, Any]] = []
    for rec in records:
        profile = compute_uncertainty_profile(rec, shadow_rows, decay_params_map)
        would_refuse = compute_would_refuse(profile)
        triggered = [s for s in profile.signals if s.triggered]
        triggered_types = sorted([s.signal_type for s in triggered])
        results.append({
            "run_id": str(profile.run_id),
            "would_refuse": would_refuse,
            "triggered_count": len(triggered),
            "triggered_signals": ",".join(triggered_types) if triggered_types else "",
            "signals": [s.to_dict() for s in profile.signals],
        })

    results.sort(key=lambda x: x["run_id"])

    csv_path = out_dir / CSV_NAME
    json_path = out_dir / JSON_NAME
    fieldnames = ["run_id", "would_refuse", "triggered_count", "triggered_signals"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow({k: r[k] for k in fieldnames})

    payload = {
        "computed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "row_count": len(results),
        "rows": results,
    }
    json_path.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str), encoding="utf-8")

    log_uncertainty_shadow_written(len(results))
    log_uncertainty_shadow_end(len(results), time.perf_counter() - t_start)
    return {
        "row_count": len(results),
        "report_path_csv": str(csv_path),
        "report_path_json": str(json_path),
    }
