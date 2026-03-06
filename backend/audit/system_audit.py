from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AuditConfig:
    min_samples: int = 50
    low_precision_threshold: float = 0.52
    high_refusal_threshold: float = 0.75
    calibration_drift_threshold: float = 0.15
    version: str = "v0"


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _group_by_market(outputs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_market: Dict[str, List[Dict[str, Any]]] = {}
    for o in outputs:
        if not isinstance(o, dict):
            continue
        market = o.get("market") or "default"
        by_market.setdefault(str(market), []).append(o)
    return by_market


def _precision_from_outputs(outputs: List[Dict[str, Any]]) -> Tuple[int, int, float]:
    go_rows = [o for o in outputs if o.get("decision") == "GO"]
    go_count = len(go_rows)
    correct_go = 0
    for o in go_rows:
        outcome = o.get("outcome")
        if outcome in (1, True):
            correct_go += 1
    precision = correct_go / float(go_count) if go_count > 0 else 0.0
    return go_count, correct_go, precision


def generate_audit(report: Dict[str, Any], cfg: AuditConfig) -> Dict[str, Any]:
    """
    Generate a deterministic system self-audit summary from an evaluation report.
    """
    de_metrics = report.get("decision_engine_metrics") or {}
    de_outputs: List[Dict[str, Any]] = report.get("decision_engine_outputs") or []

    summary = de_metrics.get("summary") or {}
    n_predictions = int(summary.get("n") or len(de_outputs) or len(report.get("predictions") or []))
    go = int(summary.get("go") or 0)
    no_go = int(summary.get("no_go") or 0)

    if "go_rate" in summary:
        go_rate = _safe_float(summary.get("go_rate"), 0.0)
    else:
        go_rate = go / float(n_predictions) if n_predictions > 0 else 0.0
    no_go_rate = 1.0 - go_rate if n_predictions > 0 else 0.0

    avg_conf_raw = _safe_float(de_metrics.get("avg_conf_raw"), 0.0)
    avg_conf_cal = _safe_float(de_metrics.get("avg_conf_cal"), 0.0)
    calibration_drift_global = abs(avg_conf_raw - avg_conf_cal)

    # Realized global precision based on actual GO decisions.
    _, _, global_precision = _precision_from_outputs(de_outputs)

    global_metrics: Dict[str, Any] = {
        "n_predictions": n_predictions,
        "go_rate": round(go_rate, 4),
        "no_go_rate": round(no_go_rate, 4),
        "avg_conf_raw": round(avg_conf_raw, 4),
        "avg_conf_cal": round(avg_conf_cal, 4),
        "calibration_drift": round(calibration_drift_global, 4),
        "precision": round(global_precision, 4),
    }

    # Per-market metrics based on decision_engine_outputs where available.
    per_market_metrics: Dict[str, Dict[str, Any]] = {}
    by_market = _group_by_market(de_outputs)
    for market in sorted(by_market.keys()):
        outs = by_market[market]
        n_mkt = len(outs)
        go_count_mkt, correct_go_mkt, prec_mkt = _precision_from_outputs(outs)
        go_rate_mkt = go_count_mkt / float(n_mkt) if n_mkt > 0 else 0.0
        no_go_rate_mkt = 1.0 - go_rate_mkt if n_mkt > 0 else 0.0

        # Per-market calibration drift from outputs if present.
        sum_raw = 0.0
        sum_cal = 0.0
        count_conf = 0
        for o in outs:
            if "conf_raw" in o and "conf_cal" in o:
                sum_raw += _safe_float(o.get("conf_raw"))
                sum_cal += _safe_float(o.get("conf_cal"))
                count_conf += 1
        if count_conf > 0:
            avg_raw_m = sum_raw / float(count_conf)
            avg_cal_m = sum_cal / float(count_conf)
        else:
            avg_raw_m = avg_conf_raw
            avg_cal_m = avg_conf_cal
        drift_m = abs(avg_raw_m - avg_cal_m)

        per_market_metrics[market] = {
            "n_predictions": n_mkt,
            "go_rate": round(go_rate_mkt, 4),
            "no_go_rate": round(no_go_rate_mkt, 4),
            "avg_conf_raw": round(avg_raw_m, 4),
            "avg_conf_cal": round(avg_cal_m, 4),
            "calibration_drift": round(drift_m, 4),
            "precision": round(prec_mkt, 4),
        }

    # Red flag detection
    red_flags: List[Dict[str, Any]] = []

    # Helper to add flags consistently.
    def _maybe_flag(flag_type: str, market: str, value: float, n: int) -> None:
        if n < cfg.min_samples:
            return
        red_flags.append(
            {
                "type": flag_type,
                "market": market,
                "value": round(value, 4),
            }
        )

    # Global flags.
    _maybe_flag("low_precision_market", "global", global_precision, n_predictions)
    _maybe_flag("excessive_refusal_rate", "global", no_go_rate, n_predictions)
    _maybe_flag("calibration_drift", "global", calibration_drift_global, n_predictions)

    # Per-market flags.
    for market in sorted(per_market_metrics.keys()):
        m = per_market_metrics[market]
        n_mkt = int(m["n_predictions"])
        prec_mkt = float(m["precision"])
        no_go_rate_mkt = float(m["no_go_rate"])
        drift_m = float(m["calibration_drift"])

        if prec_mkt < cfg.low_precision_threshold:
            _maybe_flag("low_precision_market", market, prec_mkt, n_mkt)
        if no_go_rate_mkt > cfg.high_refusal_threshold:
            _maybe_flag("excessive_refusal_rate", market, no_go_rate_mkt, n_mkt)
        if drift_m > cfg.calibration_drift_threshold:
            _maybe_flag("calibration_drift", market, drift_m, n_mkt)

    # Apply thresholds for global flags (after collecting).
    filtered_flags: List[Dict[str, Any]] = []
    for f in red_flags:
        t = f["type"]
        v = float(f["value"])
        if t == "low_precision_market" and v >= cfg.low_precision_threshold:
            continue
        if t == "excessive_refusal_rate" and v <= cfg.high_refusal_threshold:
            continue
        if t == "calibration_drift" and v <= cfg.calibration_drift_threshold:
            continue
        filtered_flags.append(f)

    # Deterministic ordering of flags.
    filtered_flags.sort(key=lambda f: (f["type"], f["market"]))

    return {
        "version": cfg.version,
        "global_metrics": global_metrics,
        "per_market_metrics": per_market_metrics,
        "red_flags": filtered_flags,
    }

