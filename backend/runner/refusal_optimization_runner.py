"""
Refusal optimization run mode (shadow-only): grid search over thresholds, write artifacts.
Uses uncertainty-shadow + evaluation outcomes; no enforcement. Must NOT run by default.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, List, Optional

from optimization.refusal_shadow import (
    ShadowDecision,
    full_grid_results,
    grid_search_best_thresholds,
)
from optimization.refusal_shadow.model import STALE_BANDS, effective_confidence_grid
from ops.ops_events import (
    log_refusal_opt_end,
    log_refusal_opt_missing_inputs,
    log_refusal_opt_start,
    log_refusal_opt_written,
)

MODE_REFUSAL_OPTIMIZE_SHADOW = "refusal-optimize-shadow"
MARKETS = ("one_x_two", "over_under_25", "gg_ng")

BEST_OVERALL_JSON = "refusal_optimization_best_overall.json"
BEST_BY_MARKET_JSON = "refusal_optimization_best_by_market.json"
GRID_SUMMARY_CSV = "refusal_optimization_grid_summary.csv"
NOTES_MD = "refusal_optimization_notes.md"


def load_decisions_from_storage(reports_dir: str | Path) -> tuple[List[ShadowDecision], bool]:
    """
    Load ShadowDecision list from existing storage (e.g. H3 uncertainty-shadow + evaluation).
    If REFUSAL_OPT_INPUT_JSON is set, load from that path under reports_dir (or absolute).
    Otherwise returns ([], True) to indicate missing inputs (emit event, write empty artifacts).
    Returns (decisions, had_input).
    """
    import os

    path_env = os.environ.get("REFUSAL_OPT_INPUT_JSON")
    if not path_env or not path_env.strip():
        return [], False

    path = Path(path_env.strip())
    if not path.is_absolute():
        path = Path(reports_dir) / path

    if not path.exists():
        return [], False

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], False

    decisions: List[ShadowDecision] = []
    for row in data.get("decisions") or []:
        try:
            d = ShadowDecision(
                effective_confidence=float(row.get("effective_confidence", 0)),
                age_band=str(row.get("age_band", "6-24h")),
                outcome=str(row.get("outcome", "NEUTRAL")),
                market=row.get("market"),
                fixture_id=row.get("fixture_id"),
            )
            if d.age_band not in STALE_BANDS:
                continue
            decisions.append(d)
        except (TypeError, ValueError):
            continue

    return decisions, True


def _best_to_dict(bt: Any) -> dict:
    return {
        "effective_confidence_threshold": bt.effective_confidence_threshold,
        "stale_band_threshold": bt.stale_band_threshold,
        "refusal_rate": bt.refusal_rate,
        "accuracy_on_non_refused": bt.accuracy_on_non_refused,
        "safety_score": bt.safety_score,
        "support_total": bt.support_total,
        "support_refused": bt.support_refused,
        "support_non_refused": bt.support_non_refused,
        "success_non_refused": bt.success_non_refused,
        "failure_non_refused": bt.failure_non_refused,
    }


def run_refusal_optimization(
    reports_dir: str | Path = "reports",
    decisions: Optional[List[ShadowDecision]] = None,
) -> dict[str, Any]:
    """
    Run grid search and write artifacts. If decisions is None, load from storage (or empty).
    Returns summary dict with error, decisions_count, artifact_paths.
    """
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)

    log_refusal_opt_start(str(reports_path))
    t0 = time.perf_counter()

    if decisions is None:
        decisions, had_input = load_decisions_from_storage(reports_path)
        if not had_input or not decisions:
            log_refusal_opt_missing_inputs("no uncertainty-shadow input or empty decisions")
            _write_empty_artifacts(reports_path)
            artifact_paths = [
                str(reports_path / BEST_OVERALL_JSON),
                str(reports_path / BEST_BY_MARKET_JSON),
                str(reports_path / GRID_SUMMARY_CSV),
                str(reports_path / NOTES_MD),
            ]
            log_refusal_opt_written(artifact_paths)
            log_refusal_opt_end(str(reports_path), time.perf_counter() - t0, 0, 4)
            return {
                "error": None,
                "detail": "no input data",
                "decisions_count": 0,
                "artifact_paths": artifact_paths,
            }

    markets_list = list(MARKETS)
    best = grid_search_best_thresholds(decisions, markets=markets_list)
    grid_rows = full_grid_results(decisions, markets=markets_list)

    # 1) best_overall.json
    overall = best.get(None)
    path_overall = reports_path / BEST_OVERALL_JSON
    path_overall.write_text(
        json.dumps(_best_to_dict(overall) if overall else {}, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    # 2) best_by_market.json
    by_market = {m: _best_to_dict(best[m]) for m in markets_list if m in best}
    path_by_market = reports_path / BEST_BY_MARKET_JSON
    path_by_market.write_text(json.dumps(by_market, sort_keys=True, indent=2), encoding="utf-8")

    # 3) grid_summary.csv
    path_csv = reports_path / GRID_SUMMARY_CSV
    with path_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["market", "stale_band_threshold", "effective_confidence_threshold", "refusal_rate", "accuracy_on_non_refused", "safety_score", "support_total"])
        for row in grid_rows:
            market_key, eff, stale, rr, acc, safety, total = row
            w.writerow([market_key if market_key is not None else "overall", stale, eff, rr, acc, safety, total])

    # 4) notes.md
    path_notes = reports_path / NOTES_MD
    path_notes.write_text(_notes_content(), encoding="utf-8")

    artifact_paths = [str(path_overall), str(path_by_market), str(path_csv), str(path_notes)]
    log_refusal_opt_written(artifact_paths)
    log_refusal_opt_end(str(reports_path), time.perf_counter() - t0, len(decisions), 4)

    return {
        "error": None,
        "decisions_count": len(decisions),
        "artifact_paths": artifact_paths,
    }


def _write_empty_artifacts(reports_path: Path) -> None:
    (reports_path / BEST_OVERALL_JSON).write_text("{}", encoding="utf-8")
    (reports_path / BEST_BY_MARKET_JSON).write_text("{}", encoding="utf-8")
    with (reports_path / GRID_SUMMARY_CSV).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["market", "stale_band_threshold", "effective_confidence_threshold", "refusal_rate", "accuracy_on_non_refused", "safety_score", "support_total"])
    (reports_path / NOTES_MD).write_text(_notes_content(), encoding="utf-8")


def _notes_content() -> str:
    return """# Refusal optimization (shadow-only)

## Fixed objective

- **safety_score** = accuracy_on_non_refused - 0.10 × refusal_rate
- **accuracy_on_non_refused**: success / (success + failure), neutrals excluded.
- Maximize safety_score over the grid.

## Grid ranges

- **effective_confidence_threshold**: 0.10 to 0.90 in steps of 0.05 (17 values).
- **stale_band_threshold**: 6-24h, 1-3d, 3-7d, 7d+.

## Tie-breaker rules

1. Higher safety_score
2. Lower refusal_rate
3. Higher accuracy_on_non_refused
4. Lower effective_confidence_threshold
5. Earlier stale band (6-24h before 1-3d before 3-7d before 7d+)

## Shadow-only, no enforcement

This optimization is for review only. It does **not** change analyzer outputs or enforce refusals in production.
"""
