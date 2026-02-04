"""
In-process evaluation report builder from analysis runs + snapshot resolutions.
Reusable by shadow pipeline and by a CLI (tools/offline_evaluator.py) that calls this.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.analysis_run_repo import AnalysisRunRepository
from repositories.prediction_repo import PredictionRepository
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository

CONFIDENCE_BANDS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.00)]
MARKETS = ("one_x_two", "over_under_25", "gg_ng")


def _band_label(lo: float, hi: float) -> str:
    return f"{lo:.2f}-{hi:.2f}"


async def build_evaluation_report(
    session: AsyncSession,
    from_utc: Optional[datetime] = None,
    to_utc: Optional[datetime] = None,
    limit: int = 5000,
) -> Dict[str, Any]:
    """
    Load runs and resolutions, aggregate per-market accuracy and reason effectiveness.
    Returns same structure as evaluation_report.json (overall, per_market_accuracy, reason_effectiveness).
    """
    run_repo = AnalysisRunRepository(session)
    resolution_repo = SnapshotResolutionRepository(session)
    pred_repo = PredictionRepository(session)

    runs = await run_repo.list_by_created_between(from_utc=from_utc, to_utc=to_utc, limit=limit)
    total_snapshots = len(runs)

    resolved: List[tuple[Any, Any]] = []
    for run in runs:
        res = await resolution_repo.get_by_analysis_run_id(run.id)
        if res is not None:
            resolved.append((run, res))

    resolved_snapshots = len(resolved)

    per_market: Dict[str, Dict[str, int]] = {
        m: {"success_count": 0, "failure_count": 0, "neutral_count": 0} for m in MARKETS
    }
    bands_label = [f"{lo:.2f}-{hi:.2f}" for lo, hi in CONFIDENCE_BANDS]
    per_market_bands: Dict[str, Dict[str, Dict[str, int]]] = {
        m: {b: {"success_count": 0, "failure_count": 0, "neutral_count": 0} for b in bands_label}
        for m in MARKETS
    }
    reason_stats: Dict[str, Dict[str, Dict[str, int]]] = {}

    for run, res in resolved:
        try:
            mo = json.loads(res.market_outcomes_json) if isinstance(res.market_outcomes_json, str) else (res.market_outcomes_json or {})
        except (TypeError, ValueError):
            mo = {}
        for m in MARKETS:
            outcome = mo.get(m, "UNRESOLVED")
            if outcome == "SUCCESS":
                per_market[m]["success_count"] += 1
            elif outcome == "FAILURE":
                per_market[m]["failure_count"] += 1
            else:
                per_market[m]["neutral_count"] += 1

        preds = await pred_repo.list_by_analysis_run(run.id)
        market_to_confidence: Dict[str, float] = {}
        key_map = {"1X2": "one_x_two", "OU25": "over_under_25", "OU_2.5": "over_under_25", "GGNG": "gg_ng", "BTTS": "gg_ng"}
        for p in preds:
            k = key_map.get((p.market or "").upper(), "")
            if k and k in MARKETS:
                market_to_confidence[k] = getattr(p, "confidence", None)
        for m in MARKETS:
            c = market_to_confidence.get(m)
            if c is not None:
                band = None
                for lo, hi in CONFIDENCE_BANDS:
                    if lo <= c < hi:
                        band = f"{lo:.2f}-{hi:.2f}"
                        break
                if band and band in per_market_bands[m]:
                    outcome = mo.get(m, "UNRESOLVED")
                    if outcome == "SUCCESS":
                        per_market_bands[m][band]["success_count"] += 1
                    elif outcome == "FAILURE":
                        per_market_bands[m][band]["failure_count"] += 1
                    else:
                        per_market_bands[m][band]["neutral_count"] += 1

        try:
            reason_json = json.loads(res.reason_codes_by_market_json) if isinstance(res.reason_codes_by_market_json, str) else (res.reason_codes_by_market_json or {})
        except (TypeError, ValueError):
            reason_json = {}
        for m in MARKETS:
            codes = reason_json.get(m) or []
            outcome = mo.get(m, "UNRESOLVED")
            for code in codes:
                if code not in reason_stats:
                    reason_stats[code] = {mm: {"success": 0, "failure": 0, "neutral": 0} for mm in MARKETS}
                if m not in reason_stats[code]:
                    reason_stats[code][m] = {"success": 0, "failure": 0, "neutral": 0}
                if outcome == "SUCCESS":
                    reason_stats[code][m]["success"] += 1
                elif outcome == "FAILURE":
                    reason_stats[code][m]["failure"] += 1
                else:
                    reason_stats[code][m]["neutral"] += 1

    def accuracy(s: int, f: int) -> Optional[float]:
        if s + f == 0:
            return None
        return round(s / (s + f), 4)

    per_market_report: Dict[str, Any] = {}
    for m in MARKETS:
        d = per_market[m]
        s, f, n = d["success_count"], d["failure_count"], d["neutral_count"]
        per_market_report[m] = {
            "success_count": s,
            "failure_count": f,
            "neutral_count": n,
            "accuracy": accuracy(s, f),
        }
        if any(per_market_bands[m][b]["success_count"] or per_market_bands[m][b]["failure_count"] for b in bands_label):
            per_market_report[m]["confidence_bands"] = {}
            for b in bands_label:
                sb = per_market_bands[m][b]
                if sb["success_count"] + sb["failure_count"] + sb["neutral_count"] > 0:
                    per_market_report[m]["confidence_bands"][b] = {
                        **sb,
                        "accuracy": accuracy(sb["success_count"], sb["failure_count"]),
                    }

    reason_effectiveness: Dict[str, Any] = {}
    for code, by_market in reason_stats.items():
        reason_effectiveness[code] = {}
        for m, counts in by_market.items():
            s = counts["success"]
            f = counts["failure"]
            reason_effectiveness[code][m] = {
                "success": s,
                "failure": f,
                "neutral": counts["neutral"],
                "success_rate": round(s / (s + f), 4) if (s + f) > 0 else None,
            }

    return {
        "overall": {"total_snapshots": total_snapshots, "resolved_snapshots": resolved_snapshots},
        "per_market_accuracy": per_market_report,
        "reason_effectiveness": reason_effectiveness,
    }
