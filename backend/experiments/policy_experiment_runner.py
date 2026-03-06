from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.simulation.backtest_engine import extract_rows_from_report, simulate_backtest


@dataclass
class ExperimentConfig:
    version: str = "v0"
    objective: str = "precision"  # "precision" | "f1"
    min_coverage: float = 0.20
    threshold_grid: Optional[List[float]] = None  # default 0.30..0.80 step 0.01


def default_grid() -> List[float]:
    return [round(0.30 + i * 0.01, 2) for i in range(int((0.80 - 0.30) / 0.01) + 1)]


def build_candidate_policies(markets: List[str], grid: List[float]) -> List[Dict[str, float]]:
    """
    Build simple candidate policies:
      - single global threshold applied to default
    (Keep v0 simple; per-market sweep comes later.)
    Returns list of thresholds dicts, e.g. {"default": 0.55}
    Deterministic ordering: increasing threshold.
    """
    # markets are currently unused but kept for future expansion.
    return [{"default": float(t)} for t in sorted(grid)]


def score_result(result: Dict[str, Any], objective: str) -> float:
    m = result.get("metrics") or {}
    return float(m.get(objective, 0.0))


def run_policy_experiment(report: Dict[str, Any], cfg: ExperimentConfig) -> Dict[str, Any]:
    rows = extract_rows_from_report(report)
    n = len(rows)
    grid = cfg.threshold_grid or default_grid()

    markets = sorted({str(r.get("market") or "default") for r in rows}) if rows else ["default"]
    candidates = build_candidate_policies(markets, grid)

    results: List[Dict[str, Any]] = []
    for thresholds in candidates:
        # Minimal cfg-like object for simulate_backtest
        tmp_cfg = type("TmpCfg", (object,), {"thresholds": thresholds, "version": "sim"})()
        bt = simulate_backtest(rows, cfg=tmp_cfg)  # type: ignore[arg-type]
        metrics = bt.get("metrics", {})
        cov = float(metrics.get("go_rate", 0.0))
        obj_val = score_result(bt, cfg.objective)
        results.append(
            {
                "thresholds": thresholds,
                "metrics": metrics,
                "objective": obj_val,
                "coverage": cov,
                "meets_min_coverage": cov >= cfg.min_coverage,
            }
        )

    eligible = [r for r in results if r["meets_min_coverage"]]
    pool = eligible if eligible else results

    def _key_fn(r: Dict[str, Any]) -> Any:
        t = float(r["thresholds"].get("default", 0.55))
        cov = float(r["metrics"].get("go_rate", 0.0))
        return (r["objective"], cov, t)

    best = max(pool, key=_key_fn) if pool else None

    # Build compact table sorted by threshold ascending
    table: List[Dict[str, Any]] = []
    for r in results:
        t = float(r["thresholds"].get("default", 0.55))
        m = r["metrics"]
        table.append(
            {
                "t": t,
                "go_rate": float(m.get("go_rate", 0.0)),
                "precision": float(m.get("precision", 0.0)),
                "recall": float(m.get("recall", 0.0)),
                "f1": float(m.get("f1", 0.0)),
                "meets_min_coverage": bool(r["meets_min_coverage"]),
            }
        )
    table.sort(key=lambda x: x["t"])

    return {
        "version": cfg.version,
        "n_rows": n,
        "objective": cfg.objective,
        "min_coverage": cfg.min_coverage,
        "best": best,
        "table": table,
    }


def run_from_report_path(report_path: str, cfg: ExperimentConfig) -> Dict[str, Any]:
    data = json.loads(Path(report_path).read_text())
    return run_policy_experiment(data, cfg)

