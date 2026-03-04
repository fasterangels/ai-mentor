from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class BacktestConfig:
    thresholds: Optional[Dict[str, float]] = None
    version: str = "v0"


def _norm_outcome(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, (int, float)):
        if val in (0, 1):
            return int(val)
    if isinstance(val, str):
        v = val.upper()
        if v in ("SUCCESS", "CORRECT", "TRUE", "1"):
            return 1
        if v in ("FAILURE", "INCORRECT", "FALSE", "0"):
            return 0
    return None


def _raw_outcome_from_dict(d: Dict[str, Any]) -> Any:
    for key in ("outcome", "is_correct", "success"):
        if key in d:
            return d.get(key)
    return None


def simulate_backtest(rows: List[Dict[str, Any]], cfg: BacktestConfig) -> Dict[str, Any]:
    """
    Simulate GO/NO_GO decisions over historical rows under a given threshold policy.
    """
    n = 0
    go_count = 0
    correct_go = 0
    total_correct = 0

    thresholds = cfg.thresholds or {}

    def _threshold_for_market(market: str) -> float:
        if market in thresholds:
            return float(thresholds[market])
        if "default" in thresholds:
            return float(thresholds["default"])
        return 0.55

    for r in rows:
        if not isinstance(r, dict):
            continue
        market = str(r.get("market") or "default")
        score = r.get("score")
        outcome = r.get("outcome")
        if not isinstance(score, (int, float)):
            continue
        norm_outcome = _norm_outcome(outcome)
        if norm_outcome is None:
            continue

        n += 1
        if norm_outcome == 1:
            total_correct += 1

        t = _threshold_for_market(market)
        if float(score) >= t:
            go_count += 1
            if norm_outcome == 1:
                correct_go += 1

    no_go_count = max(n - go_count, 0)
    go_rate = go_count / float(n) if n > 0 else 0.0
    precision = correct_go / float(go_count) if go_count > 0 else 0.0
    recall = correct_go / float(total_correct) if total_correct > 0 else 0.0
    denom = precision + recall
    f1 = (2.0 * precision * recall / denom) if denom > 0.0 else 0.0

    return {
        "version": cfg.version,
        "metrics": {
            "n_predictions": n,
            "go_rate": round(go_rate, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
    }


def extract_rows_from_report(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract unified backtest rows from an evaluation report.

    Prefers decision_engine_outputs where outcome is available; otherwise
    joins decision_engine_outputs with predictions to obtain outcome.
    """
    rows: List[Dict[str, Any]] = []

    de_outputs = report.get("decision_engine_outputs")

    # Direct path: outcomes present in outputs.
    if isinstance(de_outputs, list):
        direct_rows: List[Dict[str, Any]] = []
        for o in de_outputs:
            if not isinstance(o, dict):
                continue
            score = o.get("score")
            if not isinstance(score, (int, float)):
                continue
            outcome_val = _raw_outcome_from_dict(o)
            norm = _norm_outcome(outcome_val)
            if norm is None:
                continue
            market = o.get("market") or "default"
            direct_rows.append(
                {
                    "market": str(market),
                    "score": float(score),
                    "outcome": int(norm),
                }
            )
        if direct_rows:
            return direct_rows

    # Fallback: join outputs with predictions on id.
    if not isinstance(de_outputs, list):
        return rows

    predictions = report.get("predictions")
    if not isinstance(predictions, list):
        return rows

    by_id: Dict[Any, Dict[str, Any]] = {}
    for p in predictions:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if pid is None:
            continue
        outcome_val = _raw_outcome_from_dict(p)
        norm = _norm_outcome(outcome_val)
        if norm is None:
            continue
        by_id[pid] = {
            "outcome": int(norm),
            "market": p.get("market"),
        }

    for o in de_outputs:
        if not isinstance(o, dict):
            continue
        pid = o.get("id")
        score = o.get("score")
        if pid is None or not isinstance(score, (int, float)):
            continue
        info = by_id.get(pid)
        if not info:
            continue
        market = o.get("market") or info.get("market") or "default"
        rows.append(
            {
                "market": str(market),
                "score": float(score),
                "outcome": info["outcome"],
            }
        )

    return rows


def simulate_from_report(report: Dict[str, Any], cfg: BacktestConfig) -> Dict[str, Any]:
    """
    Convenience helper to run a backtest directly from an evaluation report.
    """
    rows = extract_rows_from_report(report)
    return simulate_backtest(rows, cfg)

