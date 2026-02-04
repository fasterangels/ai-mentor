"""
Decision quality deep-audit: reason effectiveness over time (with decay), reason churn,
confidence calibration, stability (pick flip, confidence volatility).
Deterministic; based only on provided history (no external IO).
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Align with evaluation/offline_eval
MARKETS = ("one_x_two", "over_under_25", "gg_ng")
CONFIDENCE_BANDS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.00)]

# Default config for decay and suggestion thresholds
DEFAULT_HALF_LIFE_RUNS = 50.0
DEFAULT_EFFECTIVENESS_DECAY_THRESHOLD = 0.1  # suggest dampening if decayed contribution drops by this
DEFAULT_CALIBRATION_DEVIATION_THRESHOLD = 0.1  # suggest band adjustment if |empirical - predicted| > this


def _band_label(lo: float, hi: float) -> str:
    return f"{lo:.2f}-{hi:.2f}"


def _band_mid(lo: float, hi: float) -> float:
    return round((lo + hi) / 2, 4)


def _parse_utc(created_at_utc: Any) -> datetime:
    """Parse created_at_utc (datetime or iso str) to timezone-aware UTC."""
    if hasattr(created_at_utc, "isoformat"):
        dt = created_at_utc
    else:
        s = str(created_at_utc).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def reason_effectiveness_over_time(
    records: List[Dict[str, Any]],
    half_life_runs: float = DEFAULT_HALF_LIFE_RUNS,
) -> Dict[str, Any]:
    """
    Per-reason effectiveness over time with exponential decay (recent runs weigh more).
    Returns: per reason, win/loss/neutral counts and decay-weighted contribution.
    """
    # records ordered by created_at_utc asc (oldest first) for "over time"
    sorted_records = sorted(records, key=lambda r: (_parse_utc(r.get("created_at_utc") or ""), r.get("run_id", 0)))
    reason_series: Dict[str, List[Dict[str, Any]]] = {}
    n = len(sorted_records)

    for i, rec in enumerate(sorted_records):
        weight = math.exp(-0.693 * (n - 1 - i) / half_life_runs) if half_life_runs > 0 else 1.0
        outcomes = rec.get("market_outcomes") or {}
        reason_codes = rec.get("reason_codes_by_market") or {}
        for market in MARKETS:
            outcome = outcomes.get(market, "UNRESOLVED")
            codes = reason_codes.get(market) or []
            for code in codes:
                if code not in reason_series:
                    reason_series[code] = []
                reason_series[code].append({
                    "run_index": i,
                    "run_id": rec.get("run_id"),
                    "outcome": outcome,
                    "weight": round(weight, 6),
                })

    result: Dict[str, Any] = {}
    for code, series in sorted(reason_series.items()):
        win = sum(1 for s in series if s["outcome"] == "SUCCESS")
        loss = sum(1 for s in series if s["outcome"] == "FAILURE")
        neutral = sum(1 for s in series if s["outcome"] not in ("SUCCESS", "FAILURE"))
        weighted_win = sum(s["weight"] for s in series if s["outcome"] == "SUCCESS")
        weighted_loss = sum(s["weight"] for s in series if s["outcome"] == "FAILURE")
        total_w = weighted_win + weighted_loss
        decayed_contribution = round(weighted_win - weighted_loss, 6) if total_w else 0.0
        result[code] = {
            "win_count": win,
            "loss_count": loss,
            "neutral_count": neutral,
            "decayed_contribution": decayed_contribution,
            "weighted_win": round(weighted_win, 6),
            "weighted_loss": round(weighted_loss, 6),
        }
    return result


def reason_churn_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reason churn: how often reasons appear/disappear across consecutive runs."""
    sorted_records = sorted(records, key=lambda r: (_parse_utc(r.get("created_at_utc") or ""), r.get("run_id", 0)))
    appearances = 0
    disappearances = 0
    transitions = 0
    prev_reasons: Optional[set] = None

    for rec in sorted_records:
        reason_codes = rec.get("reason_codes_by_market") or {}
        current = set()
        for codes in reason_codes.values():
            current.update(codes if isinstance(codes, list) else [])
        if prev_reasons is not None:
            transitions += 1
            appearances += len(current - prev_reasons)
            disappearances += len(prev_reasons - current)
        prev_reasons = current

    return {
        "total_transitions": transitions,
        "appearance_count": appearances,
        "disappearance_count": disappearances,
        "appearance_rate": round(appearances / transitions, 4) if transitions else 0.0,
        "disappearance_rate": round(disappearances / transitions, 4) if transitions else 0.0,
    }


def confidence_calibration(
    records: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Confidence calibration: predicted (band mid) vs empirical accuracy by band, per market."""
    bands_label = [_band_label(lo, hi) for lo, hi in CONFIDENCE_BANDS]
    per_market: Dict[str, Dict[str, Dict[str, Any]]] = {
        m: {b: {"success_count": 0, "failure_count": 0, "predicted_confidence": _band_mid(lo, hi)}
            for b, (lo, hi) in zip(bands_label, CONFIDENCE_BANDS)}
        for m in MARKETS
    }

    for rec in records:
        outcomes = rec.get("market_outcomes") or {}
        preds = rec.get("predictions") or []
        market_to_confidence: Dict[str, float] = {}
        for p in preds:
            market = (p.get("market") or "").strip()
            key_map = {"1X2": "one_x_two", "OU25": "over_under_25", "OU_2.5": "over_under_25", "GGNG": "gg_ng", "BTTS": "gg_ng", "one_x_two": "one_x_two", "over_under_25": "over_under_25", "gg_ng": "gg_ng"}
            m = key_map.get(market.upper() if market else "", key_map.get(market, ""))
            if m and m in MARKETS:
                market_to_confidence[m] = float(p.get("confidence", 0) or 0)
        for market in MARKETS:
            outcome = outcomes.get(market, "UNRESOLVED")
            c = market_to_confidence.get(market)
            if c is None:
                continue
            band = None
            for (lo, hi), bl in zip(CONFIDENCE_BANDS, bands_label):
                if lo <= c < hi:
                    band = bl
                    break
            if band and band in per_market[market]:
                if outcome == "SUCCESS":
                    per_market[market][band]["success_count"] += 1
                elif outcome == "FAILURE":
                    per_market[market][band]["failure_count"] += 1

    out: Dict[str, Dict[str, Any]] = {}
    for m in MARKETS:
        out[m] = {}
        for b in bands_label:
            d = per_market[m][b]
            s, f = d["success_count"], d["failure_count"]
            empirical = round(s / (s + f), 4) if (s + f) > 0 else None
            out[m][b] = {
                "predicted_confidence": d["predicted_confidence"],
                "empirical_accuracy": empirical,
                "success_count": s,
                "failure_count": f,
                "count": s + f,
            }
    return out


def stability_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pick flip rate and confidence volatility (p95 delta) across comparable runs."""
    by_match: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        mid = rec.get("match_id") or ""
        if mid not in by_match:
            by_match[mid] = []
        by_match[mid].append(rec)

    flip_count = 0
    flip_denom = 0
    confidence_deltas: List[float] = []

    for match_id, runs in by_match.items():
        runs_sorted = sorted(runs, key=lambda r: (_parse_utc(r.get("created_at_utc") or ""), r.get("run_id", 0)))
        for market in MARKETS:
            picks: List[Optional[str]] = []
            confs: List[float] = []
            for rec in runs_sorted:
                preds = rec.get("predictions") or []
                pick = None
                conf = None
                for p in preds:
                    m = (p.get("market") or "").strip().upper()
                    key_map = {"1X2": "one_x_two", "OU25": "over_under_25", "OU_2.5": "over_under_25", "GGNG": "gg_ng", "BTTS": "gg_ng"}
                    mk = key_map.get(m, "").lower() if m else ""
                    if mk == market:
                        pick = p.get("pick")
                        try:
                            conf = float(p.get("confidence") or 0)
                        except (TypeError, ValueError):
                            pass
                        break
                picks.append(pick)
                if conf is not None:
                    confs.append(conf)
            for i in range(1, len(picks)):
                if picks[i - 1] is not None and picks[i] is not None:
                    flip_denom += 1
                    if picks[i - 1] != picks[i]:
                        flip_count += 1
            for i in range(1, len(confs)):
                confidence_deltas.append(abs(confs[i] - confs[i - 1]))

    sorted_deltas = sorted(confidence_deltas) if confidence_deltas else []
    def p95(vals: List[float]) -> float:
        if not vals:
            return 0.0
        k = (len(vals) - 1) * 0.95
        f = int(k)
        c = min(f + 1, len(vals) - 1)
        return round(vals[f] + (k - f) * (vals[c] - vals[f]), 4)

    return {
        "pick_flip_count": flip_count,
        "pick_flip_denom": flip_denom,
        "pick_flip_rate": round(flip_count / flip_denom, 4) if flip_denom else 0.0,
        "confidence_volatility_p95": p95(sorted_deltas),
        "confidence_delta_count": len(confidence_deltas),
    }


def build_suggestions(
    records: List[Dict[str, Any]],
    reason_effectiveness: Dict[str, Any],
    calibration: Dict[str, Dict[str, Any]],
    effectiveness_decay_threshold: float = DEFAULT_EFFECTIVENESS_DECAY_THRESHOLD,
    calibration_deviation_threshold: float = DEFAULT_CALIBRATION_DEVIATION_THRESHOLD,
) -> Dict[str, Any]:
    """
    Guardrail suggestions only (no activation): dampening candidates, confidence band adjustments.
    """
    dampening_candidates: List[Dict[str, Any]] = []
    for code, data in reason_effectiveness.items():
        win, loss = data.get("win_count", 0), data.get("loss_count", 0)
        decayed = data.get("decayed_contribution", 0)
        total = win + loss
        if total == 0:
            continue
        recent_rate = win / total
        if decayed < 0 and abs(decayed) > effectiveness_decay_threshold:
            dampening_candidates.append({
                "reason_code": code,
                "decayed_contribution": decayed,
                "win_count": win,
                "loss_count": loss,
                "suggestion": "consider dampening weight for this reason (effectiveness degrades)",
            })

    confidence_band_adjustments: List[Dict[str, Any]] = []
    for market in MARKETS:
        for band, d in (calibration.get(market) or {}).items():
            pred = d.get("predicted_confidence")
            emp = d.get("empirical_accuracy")
            count = d.get("count", 0)
            if pred is None or emp is None or count < 5:
                continue
            dev = abs(emp - pred)
            if dev > calibration_deviation_threshold:
                confidence_band_adjustments.append({
                    "market": market,
                    "band": band,
                    "predicted_confidence": pred,
                    "empirical_accuracy": emp,
                    "deviation": round(dev, 4),
                    "count": count,
                    "suggestion": "consider shifting band or threshold to improve calibration",
                })

    return {
        "dampening_candidates": dampening_candidates,
        "confidence_band_adjustments": confidence_band_adjustments,
    }


def compute_decision_quality_report(
    records: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full decision quality report: reason effectiveness (with decay), churn, calibration,
    stability, and suggestions. Deterministic given same records and config.
    """
    config = config or {}
    half_life = float(config.get("half_life_runs", DEFAULT_HALF_LIFE_RUNS))
    eff_threshold = float(config.get("effectiveness_decay_threshold", DEFAULT_EFFECTIVENESS_DECAY_THRESHOLD))
    cal_threshold = float(config.get("calibration_deviation_threshold", DEFAULT_CALIBRATION_DEVIATION_THRESHOLD))

    reason_eff = reason_effectiveness_over_time(records, half_life_runs=half_life)
    churn = reason_churn_metrics(records)
    calibration = confidence_calibration(records)
    stability = stability_metrics(records)
    suggestions = build_suggestions(
        records,
        reason_eff,
        calibration,
        effectiveness_decay_threshold=eff_threshold,
        calibration_deviation_threshold=cal_threshold,
    )

    return {
        "summary": {
            "run_count": len(records),
            "half_life_runs": half_life,
        },
        "reason_effectiveness_over_time": reason_eff,
        "reason_churn": churn,
        "confidence_calibration": calibration,
        "stability": stability,
        "suggestions": suggestions,
    }


async def load_history_from_session(
    session: Any,
    from_utc: Optional[datetime] = None,
    to_utc: Optional[datetime] = None,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    """
    Load resolved runs + resolutions + predictions from DB into list of run records.
    For use by CLI; no external IO other than session.
    """
    from repositories.analysis_run_repo import AnalysisRunRepository
    from repositories.snapshot_resolution_repo import SnapshotResolutionRepository
    from repositories.prediction_repo import PredictionRepository

    run_repo = AnalysisRunRepository(session)
    resolution_repo = SnapshotResolutionRepository(session)
    pred_repo = PredictionRepository(session)

    runs = await run_repo.list_by_created_between(from_utc=from_utc, to_utc=to_utc, limit=limit)
    records: List[Dict[str, Any]] = []

    for run in runs:
        res = await resolution_repo.get_by_analysis_run_id(run.id)
        if res is None:
            continue
        try:
            mo = json.loads(res.market_outcomes_json) if isinstance(res.market_outcomes_json, str) else (res.market_outcomes_json or {})
        except (TypeError, ValueError):
            mo = {}
        try:
            rc = json.loads(res.reason_codes_by_market_json) if isinstance(res.reason_codes_by_market_json, str) else (res.reason_codes_by_market_json or {})
        except (TypeError, ValueError):
            rc = {}
        preds = await pred_repo.list_by_analysis_run(run.id)
        predictions = []
        for p in preds:
            reasons = []
            try:
                rj = json.loads(p.reasons_json) if getattr(p, "reasons_json", None) else []
                reasons = rj if isinstance(rj, list) else []
            except (TypeError, ValueError):
                pass
            predictions.append({
                "market": p.market,
                "pick": p.pick,
                "confidence": getattr(p, "confidence", None),
                "reasons": reasons,
            })
        created = getattr(run, "created_at_utc", None)
        records.append({
            "run_id": run.id,
            "created_at_utc": created.isoformat() if hasattr(created, "isoformat") else str(created),
            "match_id": res.match_id,
            "market_outcomes": mo,
            "reason_codes_by_market": rc,
            "predictions": predictions,
        })

    return records
