"""
Confidence penalty shadow reporting (H2 Part B). SHADOW-ONLY: no effect on decisions.
Computes hypothetical penalized confidence per evaluated decision; writes reports only.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.staleness_metrics import (
    MARKETS,
    _load_evaluation_data_with_evidence_age,
)
from modeling.confidence_penalty import compute_penalty
from modeling.reason_decay.model import DecayModelParams, params_from_dict

REPORT_SUBDIR = "confidence_penalty_shadow"
CSV_NAME = "confidence_penalty_shadow.csv"
JSON_NAME = "confidence_penalty_shadow.json"
DECAY_PARAMS_JSON = "decay_fit/reason_decay_params.json"


def _load_decay_params_map(reports_dir: str | Path) -> Dict[Tuple[str, str], DecayModelParams]:
    """Load reason_decay_params.json; return (market, reason_code) -> DecayModelParams. Deterministic."""
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


def _row_to_dict(r: Any, run_id: str) -> Dict[str, Any]:
    """One shadow row for CSV/JSON. Stable keys."""
    return {
        "age_band": r.age_band,
        "market": r.market,
        "original_confidence": round(r.original_confidence, 4),
        "penalized_confidence": round(r.penalized_confidence, 4),
        "penalty_factor": round(r.penalty_factor, 4),
        "reason_code": r.reason_code,
        "run_id": run_id,
    }


async def run_confidence_penalty_shadow(
    session: AsyncSession,
    reports_dir: str | Path = "reports",
    from_utc: Any = None,
    to_utc: Any = None,
    limit: int = 5000,
) -> Dict[str, Any]:
    """
    For each evaluated decision: compute per-reason penalty (Part A), hypothetical penalized confidence.
    Write confidence_penalty_shadow.csv and .json. No analyzer or policy change; reporting only.
    """
    from ops.ops_events import (
        log_confidence_penalty_shadow_end,
        log_confidence_penalty_shadow_start,
        log_confidence_penalty_shadow_written,
    )

    t_start = log_confidence_penalty_shadow_start()
    reports_dir = Path(reports_dir)
    out_dir = reports_dir / REPORT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)

    params_map = _load_decay_params_map(reports_dir)
    records, _ = await _load_evaluation_data_with_evidence_age(
        session, from_utc=from_utc, to_utc=to_utc, limit=limit
    )

    rows: List[Tuple[str, Any]] = []  # (run_id, PenaltyResult)
    for rec in records:
        run_id = str(rec.get("run_id", ""))
        age_band = rec.get("age_band", "0-30m")
        market_to_confidence = rec.get("market_to_confidence") or {}
        reason_codes_by_market = rec.get("reason_codes_by_market") or {}
        for market in MARKETS:
            confidence = market_to_confidence.get(market)
            if confidence is None:
                continue
            for code in reason_codes_by_market.get(market) or []:
                reason_code = str(code)
                decay_params = params_map.get((market, reason_code))
                r = compute_penalty(
                    market=market,
                    reason_code=reason_code,
                    age_band=age_band,
                    original_confidence=float(confidence),
                    decay_params=decay_params,
                )
                rows.append((run_id, r))

    # Stable ordering: run_id, market, reason_code
    rows.sort(key=lambda x: (x[0], x[1].market, x[1].reason_code))

    csv_path = out_dir / CSV_NAME
    json_path = out_dir / JSON_NAME
    fieldnames = ["run_id", "market", "reason_code", "age_band", "original_confidence", "penalty_factor", "penalized_confidence"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for run_id, r in rows:
            w.writerow(_row_to_dict(r, run_id))

    payload = {
        "computed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "row_count": len(rows),
        "rows": [_row_to_dict(r, run_id) for run_id, r in rows],
    }
    json_path.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str), encoding="utf-8")

    log_confidence_penalty_shadow_written(len(rows))
    log_confidence_penalty_shadow_end(len(rows), time.perf_counter() - t_start)
    return {
        "row_count": len(rows),
        "report_path_csv": str(csv_path),
        "report_path_json": str(json_path),
    }
