"""
In-process evaluation report builder from analysis runs + snapshot resolutions.
Reusable by shadow pipeline and by a CLI (tools/offline_evaluator.py) that calls this.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.analysis_run_repo import AnalysisRunRepository
from repositories.prediction_repo import PredictionRepository
from repositories.snapshot_resolution_repo import SnapshotResolutionRepository

CONFIDENCE_BANDS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.00)]
# Finer bands (0.00-0.10, ..., 0.90-1.00) for Phase E; deterministic ordering
CONFIDENCE_BANDS_FINE = [(i * 0.1, (i + 1) * 0.1) for i in range(10)]
# Calibration summary bands (fixed; deterministic ordering)
CALIBRATION_BANDS = [(0.0, 0.49), (0.50, 0.59), (0.60, 0.69), (0.70, 0.79), (0.80, 1.00)]
CALIBRATION_BAND_LABELS = [f"{lo:.2f}-{hi:.2f}" for lo, hi in CALIBRATION_BANDS]
MARKETS = ("one_x_two", "over_under_25", "gg_ng")


def _band_label(lo: float, hi: float) -> str:
    return f"{lo:.2f}-{hi:.2f}"


def _calibration_band_for_confidence(c: float) -> Optional[str]:
    """Return band label for confidence c; None if c is None or out of [0,1]. Bands inclusive [lo, hi]. Deterministic."""
    if c is None:
        return None
    c = float(c)
    if c < 0.0 or c > 1.0:
        return None
    for i, (lo, hi) in enumerate(CALIBRATION_BANDS):
        if lo <= c <= hi:
            return CALIBRATION_BAND_LABELS[i]
    return None


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
    bands_label_fine = [f"{lo:.2f}-{hi:.2f}" for lo, hi in CONFIDENCE_BANDS_FINE]
    per_market_bands: Dict[str, Dict[str, Dict[str, int]]] = {
        m: {b: {"success_count": 0, "failure_count": 0, "neutral_count": 0} for b in bands_label}
        for m in MARKETS
    }
    per_market_bands_fine: Dict[str, Dict[str, Dict[str, int]]] = {
        m: {b: {"success_count": 0, "failure_count": 0, "neutral_count": 0} for b in bands_label_fine}
        for m in MARKETS
    }
    reason_stats: Dict[str, Dict[str, Dict[str, int]]] = {}
    # Calibration: per market and overall, per band -> count, success, failure, neutral, sum_confidence
    cal_bands_label = CALIBRATION_BAND_LABELS
    cal_per_market: Dict[str, Dict[str, Dict[str, Any]]] = {
        m: {b: {"count_predictions": 0, "success_count": 0, "failure_count": 0, "neutral_count": 0, "sum_confidence": 0.0} for b in cal_bands_label}
        for m in MARKETS
    }
    cal_overall: Dict[str, Dict[str, Any]] = {b: {"count_predictions": 0, "success_count": 0, "failure_count": 0, "neutral_count": 0, "sum_confidence": 0.0} for b in cal_bands_label}
    # Brier: (p, y) per market; y=1 if SUCCESS else 0, only when outcome in (SUCCESS, FAILURE)
    brier_py_per_market: Dict[str, List[Tuple[float, int]]] = {m: [] for m in MARKETS}

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
                band_fine = None
                for lo, hi in CONFIDENCE_BANDS_FINE:
                    if lo <= c < hi or (lo == 0.9 and c <= 1.0):
                        band_fine = f"{lo:.2f}-{hi:.2f}"
                        break
                if band_fine and band_fine in per_market_bands_fine[m]:
                    outcome = mo.get(m, "UNRESOLVED")
                    if outcome == "SUCCESS":
                        per_market_bands_fine[m][band_fine]["success_count"] += 1
                    elif outcome == "FAILURE":
                        per_market_bands_fine[m][band_fine]["failure_count"] += 1
                    else:
                        per_market_bands_fine[m][band_fine]["neutral_count"] += 1
            # Calibration bands and Brier
            cal_band = _calibration_band_for_confidence(c) if c is not None else None
            if cal_band and cal_band in cal_per_market[m]:
                outcome = mo.get(m, "UNRESOLVED")
                cal_per_market[m][cal_band]["count_predictions"] += 1
                cal_per_market[m][cal_band]["sum_confidence"] += c
                cal_overall[cal_band]["count_predictions"] += 1
                cal_overall[cal_band]["sum_confidence"] += c
                if outcome == "SUCCESS":
                    cal_per_market[m][cal_band]["success_count"] += 1
                    cal_overall[cal_band]["success_count"] += 1
                elif outcome == "FAILURE":
                    cal_per_market[m][cal_band]["failure_count"] += 1
                    cal_overall[cal_band]["failure_count"] += 1
                else:
                    cal_per_market[m][cal_band]["neutral_count"] += 1
                    cal_overall[cal_band]["neutral_count"] += 1
                if outcome in ("SUCCESS", "FAILURE"):
                    brier_py_per_market[m].append((c, 1 if outcome == "SUCCESS" else 0))

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
        per_market_report[m]["confidence_bands_fine"] = {}
        for b in bands_label_fine:
            sb = per_market_bands_fine[m][b]
            total = sb["success_count"] + sb["failure_count"] + sb["neutral_count"]
            if total > 0:
                per_market_report[m]["confidence_bands_fine"][b] = {
                    **sb,
                    "count": total,
                    "accuracy": accuracy(sb["success_count"], sb["failure_count"]),
                    "neutrals_rate": round(sb["neutral_count"] / total, 4),
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

    # Build calibration_summary (deterministic ordering: bands, then markets)
    def _band_summary(d: Dict[str, Any]) -> Dict[str, Any]:
        n = d["count_predictions"]
        s, f, neut = d["success_count"], d["failure_count"], d["neutral_count"]
        acc = round(s / (s + f), 4) if (s + f) > 0 else None
        avg_conf = round(d["sum_confidence"] / n, 4) if n > 0 else None
        return {
            "count_predictions": n,
            "accuracy": acc,
            "neutral_count": neut,
            "average_confidence": avg_conf,
        }

    confidence_bands: Dict[str, Any] = {}
    for m in MARKETS:
        confidence_bands[m] = {}
        for b in cal_bands_label:
            if cal_per_market[m][b]["count_predictions"] > 0:
                confidence_bands[m][b] = _band_summary(cal_per_market[m][b])
    confidence_bands["overall"] = {}
    for b in cal_bands_label:
        if cal_overall[b]["count_predictions"] > 0:
            confidence_bands["overall"][b] = _band_summary(cal_overall[b])

    def _brier(py_list: List[Tuple[float, int]]) -> Optional[float]:
        if not py_list:
            return None
        return round(sum((p - y) ** 2 for p, y in py_list) / len(py_list), 4)

    brier_by_market: Dict[str, Any] = {}
    all_py: List[Tuple[float, int]] = []
    for m in MARKETS:
        b = _brier(brier_py_per_market[m])
        if b is not None:
            brier_by_market[m] = b
        all_py.extend(brier_py_per_market[m])
    brier_overall = _brier(all_py)

    calibration_summary: Dict[str, Any] = {
        "confidence_bands": confidence_bands,
        "brier_scores": {
            "brier_by_market": brier_by_market,
            "brier_overall": brier_overall,
        },
    }

    return {
        "overall": {"total_snapshots": total_snapshots, "resolved_snapshots": resolved_snapshots},
        "per_market_accuracy": per_market_report,
        "reason_effectiveness": reason_effectiveness,
        "calibration_summary": calibration_summary,
    }
