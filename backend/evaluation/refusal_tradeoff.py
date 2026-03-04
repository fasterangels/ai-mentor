from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TradeoffConfig:
    thresholds: Optional[List[float]] = None
    version: str = "v0"


def _default_thresholds() -> List[float]:
    start, end, step = 0.30, 0.80, 0.01
    n_steps = int(round((end - start) / step))
    return [round(start + i * step, 2) for i in range(n_steps + 1)]


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
    """
    Look up an outcome-like field without treating 0 as falsy.
    """
    for key in ("outcome", "is_correct", "success"):
        if key in d:
            return d.get(key)
    return None


def compute_tradeoff(rows: List[Dict[str, Any]], cfg: TradeoffConfig) -> Dict[str, Any]:
    """
    Compute coverage/precision/recall/F1 tradeoff curves per market and globally.
    """
    thresholds = list(cfg.thresholds) if cfg.thresholds is not None else _default_thresholds()
    thresholds = sorted(set(float(t) for t in thresholds))

    result: Dict[str, Any] = {
        "version": cfg.version,
        "global": {"points": []},
        "per_market": {},
    }

    if not rows:
        return result

    # Group rows by market
    by_market: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        m = str(r.get("market") or "default")
        by_market.setdefault(m, []).append(r)

    def _points_for(rlist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        n = len(rlist)
        if n == 0:
            return []
        total_correct = sum(int(r["outcome"]) for r in rlist)
        points: List[Dict[str, Any]] = []
        for t in thresholds:
            go_rows = [r for r in rlist if float(r["score"]) >= t]
            go_count = len(go_rows)
            coverage = go_count / float(n)
            correct_go = sum(int(r["outcome"]) for r in go_rows)

            precision = correct_go / float(go_count) if go_count > 0 else 0.0
            recall = correct_go / float(total_correct) if total_correct > 0 else 0.0

            denom = precision + recall
            f1 = (2.0 * precision * recall / denom) if denom > 0.0 else 0.0

            points.append(
                {
                    "t": t,
                    "coverage": round(coverage, 4),
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "go": go_count,
                    "n": n,
                }
            )
        return points

    # Global
    result["global"]["points"] = _points_for(rows)

    # Per-market, sorted by market key
    per_market: Dict[str, Any] = {}
    for market in sorted(by_market.keys()):
        per_market[market] = {"points": _points_for(by_market[market])}
    result["per_market"] = per_market

    return result


def extract_rows_for_tradeoff(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract rows suitable for refusal tradeoff computation.

    Preferred source is report["decision_engine_outputs"], which should contain
      - market
      - score
      - outcome (0/1) if available

    If outcomes are only present in predictions, we join by id.
    """
    rows: List[Dict[str, Any]] = []

    de_outputs = report.get("decision_engine_outputs")

    # Direct extraction when outcome is present on outputs.
    if isinstance(de_outputs, list):
        direct_rows: List[Dict[str, Any]] = []
        for o in de_outputs:
            if not isinstance(o, dict):
                continue
            outcome_val = _raw_outcome_from_dict(o)
            norm = _norm_outcome(outcome_val)
            if norm is None:
                continue
            score = o.get("score")
            if not isinstance(score, (int, float)):
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

    # Fallback: join outputs with predictions on id to obtain outcome.
    if not isinstance(de_outputs, list):
        return []

    predictions = report.get("predictions")
    if not isinstance(predictions, list):
        return []

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
        by_id[pid] = {"outcome": int(norm), "market": p.get("market")}

    for o in de_outputs:
        if not isinstance(o, dict):
            continue
        pid = o.get("id")
        score = o.get("score")
        if pid is None or not isinstance(score, (int, float)):
            continue
        pred_info = by_id.get(pid)
        if not pred_info:
            continue
        market = o.get("market") or pred_info.get("market") or "default"
        rows.append(
            {
                "market": str(market),
                "score": float(score),
                "outcome": pred_info["outcome"],
            }
        )

    return rows

