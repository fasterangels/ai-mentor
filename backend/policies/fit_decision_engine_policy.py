from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from backend.policies.decision_engine_policy import (
    DEFAULT_THRESHOLD,
    DecisionPolicy,
    save_policy,
)


@dataclass
class FitConfig:
    """
    Configuration for offline threshold fitting.

    Attributes:
        min_coverage: Minimum fraction of decisions that should be GO.
        objective: "precision" or "f1".
        threshold_grid: Optional explicit list of thresholds to search.
        version: Policy version to write once fitted.
    """

    min_coverage: float = 0.20
    objective: str = "precision"
    threshold_grid: Optional[List[float]] = None
    version: str = "v1"


def _default_threshold_grid() -> List[float]:
    # Deterministic grid from 0.30 to 0.80 inclusive, step 0.01.
    start, end, step = 0.30, 0.80, 0.01
    n_steps = int(round((end - start) / step))  # 50 steps
    return [round(start + i * step, 2) for i in range(n_steps + 1)]


def extract_training_rows(report: Dict) -> List[Dict[str, object]]:
    """
    Extract training rows from an offline evaluation report.

    Each returned row has:
      {"market": str, "score": float, "outcome": int}

    Supported shapes (best-effort):
      A) report["predictions"] list with "outcome" and a decision engine score.
      B) report["decision_engine_outputs"] list if present.
      C) report["decision_engine_metrics"]["examples"] + predictions lookup by id.
    """
    rows: List[Dict[str, object]] = []

    def _norm_outcome(val: object) -> Optional[int]:
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

    def _append_row(market: object, score: object, outcome: object) -> None:
        m = str(market) if isinstance(market, str) else "default"
        if not isinstance(score, (int, float)):
            return
        o = _norm_outcome(outcome)
        if o is None:
            return
        rows.append({"market": m, "score": float(score), "outcome": int(o)})

    # Shape A: direct predictions list
    predictions = report.get("predictions")
    if isinstance(predictions, list):
        for p in predictions:
            if not isinstance(p, dict):
                continue
            market = p.get("market") or (p.get("meta") or {}).get("market") or "default"
            outcome = p.get("outcome")
            # Attempt several score locations.
            score = (
                p.get("decision_engine_score")
                or (p.get("decision_engine") or {}).get("score")
                or p.get("score")
            )
            _append_row(market, score, outcome)

    if rows:
        return rows

    # Shape B: decision_engine_outputs list
    de_outputs = report.get("decision_engine_outputs")
    if isinstance(de_outputs, list):
        for o in de_outputs:
            if not isinstance(o, dict):
                continue
            market = o.get("market") or "default"
            score = o.get("score")
            outcome = o.get("outcome")
            _append_row(market, score, outcome)

    if rows:
        return rows

    # Shape C: metrics examples + predictions lookup by id
    metrics = report.get("decision_engine_metrics") or {}
    examples = metrics.get("examples") or []
    if isinstance(examples, list) and isinstance(predictions, list):
        by_id: Dict[object, Dict] = {}
        for p in predictions:
            if not isinstance(p, dict):
                continue
            pid = p.get("id")
            if pid is not None:
                by_id[pid] = p

        for ex in examples:
            if not isinstance(ex, dict):
                continue
            pid = ex.get("id")
            p = by_id.get(pid)
            if not p:
                continue
            market = ex.get("market") or p.get("market") or "default"
            score = ex.get("score")
            outcome = p.get("outcome")
            _append_row(market, score, outcome)

    return rows


def fit_threshold_for_market(rows: List[Dict[str, object]], cfg: FitConfig) -> float:
    """
    Fit a threshold for a single market according to the chosen objective.

    Tie-breakers (in order):
      1) higher coverage
      2) higher threshold
    """
    n = len(rows)
    if n == 0:
        return DEFAULT_THRESHOLD

    total_correct = sum(int(r["outcome"]) for r in rows)

    grid = list(cfg.threshold_grid) if cfg.threshold_grid is not None else _default_threshold_grid()

    candidates: List[Tuple[float, float, float]] = []  # (threshold, coverage, objective)
    for t in grid:
        go_rows = [r for r in rows if float(r["score"]) >= t]
        go_count = len(go_rows)
        coverage = go_count / float(n)
        correct_go = sum(int(r["outcome"]) for r in go_rows)

        precision = correct_go / float(go_count) if go_count > 0 else 0.0
        recall = correct_go / float(total_correct) if total_correct > 0 else 0.0

        if cfg.objective == "f1":
            denom = precision + recall
            objective_val = (2.0 * precision * recall / denom) if denom > 0.0 else 0.0
        else:
            objective_val = precision

        candidates.append((float(t), coverage, objective_val))

    # First, respect min_coverage if possible.
    eligible = [c for c in candidates if c[1] >= cfg.min_coverage]
    if not eligible:
        eligible = candidates

    # Sort by objective desc, then coverage desc, then threshold desc.
    eligible.sort(key=lambda x: (x[2], x[1], x[0]), reverse=True)
    best_t, _, _ = eligible[0]
    return best_t


def fit_policy(rows: List[Dict[str, object]], cfg: FitConfig) -> DecisionPolicy:
    """
    Fit per-market thresholds and assemble a DecisionPolicy.

    Always includes a "default" threshold based on all rows. Markets
    with fewer than 20 rows fall back to the default threshold.
    """
    if not rows:
        return DecisionPolicy(version=cfg.version, thresholds={"default": DEFAULT_THRESHOLD})

    # Group rows by market
    by_market: Dict[str, List[Dict[str, object]]] = {}
    for r in rows:
        market = str(r.get("market") or "default")
        by_market.setdefault(market, []).append(r)

    default_threshold = fit_threshold_for_market(rows, cfg)
    thresholds: Dict[str, float] = {"default": default_threshold}

    for market, m_rows in by_market.items():
        if len(m_rows) < 20:
            thresholds[market] = default_threshold
        else:
            thresholds[market] = fit_threshold_for_market(m_rows, cfg)

    return DecisionPolicy(version=cfg.version, thresholds=thresholds)


def fit_and_save_policy_from_report(
    report_path: str,
    policy_path: str,
    cfg: FitConfig,
) -> DecisionPolicy:
    """
    Load an evaluation report, fit thresholds per market, and save policy JSON.
    """
    report_file = Path(report_path)
    data = json.loads(report_file.read_text())

    rows = extract_training_rows(data)
    if not rows:
        policy = DecisionPolicy(version=cfg.version, thresholds={"default": DEFAULT_THRESHOLD})
    else:
        policy = fit_policy(rows, cfg)
        policy.version = cfg.version

    save_policy(policy, policy_path)
    return policy

