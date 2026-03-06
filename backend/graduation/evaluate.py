"""
Graduation evaluator: compute PASS/FAIL per criterion and overall from existing reports.
Deterministic; same inputs -> same result. Missing artifact -> criterion FAIL with detail.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .criteria_v1 import (
    CriterionResult,
    DEFAULT_DECAY_MIN_REASON_CODES,
    DEFAULT_DELTA_COVERAGE_MIN_FIXTURES,
    DEFAULT_DELTA_PAYLOAD_MATCH_MIN_RATE,
    DEFAULT_STALENESS_MIN_REASON_CODES,
    DEFAULT_UNCERTAINTY_MIN_DECISIONS,
    DEFAULT_WORST_CASE_MIN_ROWS,
    GraduationResult,
    LATE_DATA_ACCURACY_DELTA_24H_MIN,
    LATE_DATA_REFUSAL_DELTA_24H_MIN,
)

# Conventional artifact paths under reports_dir
DELTA_EVAL_DIR = "delta_eval"
STALENESS_EVAL_JSON = "staleness_eval/staleness_metrics_by_reason.json"
DECAY_FIT_JSON = "decay_fit/reason_decay_params.json"
UNCERTAINTY_SHADOW_JSON = "uncertainty_shadow_decisions.json"
LATE_DATA_SUMMARY_JSON = "replay_scenarios/late_data/late_data_summary.json"
WORST_CASE_JSON = "worst_case_errors_top.json"
REFUSAL_OPT_BEST_JSON = "refusal_optimization_best_overall.json"
REFUSAL_OPT_GRID_CSV = "refusal_optimization_grid_summary.csv"

# Deterministic criterion order
CRITERION_ORDER = [
    "DELTA_COVERAGE",
    "DELTA_PAYLOAD_MATCH_RATE",
    "STALENESS_OBSERVABILITY",
    "DECAY_MODEL_COVERAGE",
    "UNCERTAINTY_SIGNAL_AVAILABILITY",
    "LATE_DATA_ROBUSTNESS",
    "WORST_CASE_VISIBILITY",
    "REFUSAL_OPT_REPORTING",
]


def _safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _check_delta_coverage(reports_dir: Path, min_fixtures: int) -> CriterionResult:
    """G3: at least N fixtures with both recorded and live_shadow deltas."""
    delta_dir = reports_dir / DELTA_EVAL_DIR
    if not delta_dir.exists():
        return CriterionResult("DELTA_COVERAGE", False, {"reason": "delta_eval dir missing", "path": str(delta_dir)})
    files = sorted(delta_dir.glob("delta_eval_*.json"))
    if not files:
        return CriterionResult("DELTA_COVERAGE", False, {"reason": "no delta_eval_*.json files", "path": str(delta_dir)})
    total_with_both = 0
    for f in files:
        data = _safe_read_json(f)
        if not data or "reports" not in data:
            continue
        for r in data.get("reports") or []:
            if r.get("recorded_snapshot_id") and r.get("live_snapshot_id"):
                total_with_both += 1
    pass_ = total_with_both >= min_fixtures
    return CriterionResult(
        "DELTA_COVERAGE",
        pass_,
        {"fixtures_with_both_deltas": total_with_both, "min_required": min_fixtures},
    )


def _check_delta_payload_match_rate(reports_dir: Path, min_rate: float) -> CriterionResult:
    """G3: payload_match rate >= min_rate."""
    delta_dir = reports_dir / DELTA_EVAL_DIR
    if not delta_dir.exists():
        return CriterionResult("DELTA_PAYLOAD_MATCH_RATE", False, {"reason": "delta_eval dir missing"})
    files = sorted(delta_dir.glob("delta_eval_*.json"))
    matches = 0
    total = 0
    for f in files:
        data = _safe_read_json(f)
        if not data or "reports" not in data:
            continue
        for r in data.get("reports") or []:
            total += 1
            if r.get("payload_match") is True:
                matches += 1
    rate = matches / total if total else 0.0
    pass_ = total > 0 and rate >= min_rate
    return CriterionResult(
        "DELTA_PAYLOAD_MATCH_RATE",
        pass_,
        {"payload_match_rate": round(rate, 4), "min_required": min_rate, "total_reports": total},
    )


def _check_staleness_observability(reports_dir: Path, min_reason_codes: int) -> CriterionResult:
    """G4: report exists and >= M reason_codes with non-zero support."""
    path = reports_dir / STALENESS_EVAL_JSON
    data = _safe_read_json(path)
    if not data:
        return CriterionResult("STALENESS_OBSERVABILITY", False, {"reason": "artifact missing", "path": str(path)})
    rows = data.get("rows") or []
    reason_codes_with_support = set()
    for row in rows:
        if (row.get("total") or 0) > 0 and row.get("reason_code"):
            reason_codes_with_support.add(str(row["reason_code"]))
    count = len(reason_codes_with_support)
    pass_ = count >= min_reason_codes
    return CriterionResult(
        "STALENESS_OBSERVABILITY",
        pass_,
        {"reason_codes_with_support": count, "min_required": min_reason_codes},
    )


def _check_decay_model_coverage(reports_dir: Path, min_reason_codes: int) -> CriterionResult:
    """H1: decay params for >= M reason_codes and include fit diagnostics."""
    path = reports_dir / DECAY_FIT_JSON
    data = _safe_read_json(path)
    if not data:
        return CriterionResult("DECAY_MODEL_COVERAGE", False, {"reason": "artifact missing", "path": str(path)})
    params = data.get("params") or []
    with_fit = 0
    for p in params:
        if p.get("reason_code") and p.get("fit_quality") is not None:
            with_fit += 1
    pass_ = with_fit >= min_reason_codes
    return CriterionResult(
        "DECAY_MODEL_COVERAGE",
        pass_,
        {"reason_codes_with_fit": with_fit, "min_required": min_reason_codes},
    )


def _check_uncertainty_signal_availability(reports_dir: Path, min_decisions: int) -> CriterionResult:
    """H3: uncertainty_shadow covers >= N decisions."""
    path = reports_dir / UNCERTAINTY_SHADOW_JSON
    data = _safe_read_json(path)
    if not data:
        return CriterionResult("UNCERTAINTY_SIGNAL_AVAILABILITY", False, {"reason": "artifact missing", "path": str(path)})
    decisions = data.get("decisions") or []
    count = len(decisions)
    pass_ = count >= min_decisions
    return CriterionResult(
        "UNCERTAINTY_SIGNAL_AVAILABILITY",
        pass_,
        {"decisions_count": count, "min_required": min_decisions},
    )


def _check_late_data_robustness(reports_dir: Path) -> CriterionResult:
    """I1: accuracy_delta_24h >= -0.10 OR refusal_delta_24h >= +0.05."""
    path = reports_dir / LATE_DATA_SUMMARY_JSON
    data = _safe_read_json(path)
    if not data:
        return CriterionResult("LATE_DATA_ROBUSTNESS", False, {"reason": "artifact missing", "path": str(path)})
    acc_delta = data.get("accuracy_delta_24h")
    ref_delta = data.get("refusal_delta_24h")
    if acc_delta is None and ref_delta is None:
        return CriterionResult("LATE_DATA_ROBUSTNESS", False, {"reason": "missing accuracy_delta_24h and refusal_delta_24h"})
    acc_ok = acc_delta is not None and acc_delta >= LATE_DATA_ACCURACY_DELTA_24H_MIN
    ref_ok = ref_delta is not None and ref_delta >= LATE_DATA_REFUSAL_DELTA_24H_MIN
    pass_ = acc_ok or ref_ok
    return CriterionResult(
        "LATE_DATA_ROBUSTNESS",
        pass_,
        {
            "accuracy_delta_24h": acc_delta,
            "refusal_delta_24h": ref_delta,
            "accuracy_ok": acc_ok,
            "refusal_ok": ref_ok,
        },
    )


def _check_worst_case_visibility(reports_dir: Path, min_rows: int) -> CriterionResult:
    """I2: worst-case report exists and has >= K rows."""
    path = reports_dir / WORST_CASE_JSON
    data = _safe_read_json(path)
    if not data:
        return CriterionResult("WORST_CASE_VISIBILITY", False, {"reason": "artifact missing", "path": str(path)})
    rows = data.get("rows") or []
    count = len(rows)
    pass_ = count >= min_rows
    return CriterionResult(
        "WORST_CASE_VISIBILITY",
        pass_,
        {"rows_count": count, "min_required": min_rows},
    )


def _check_refusal_opt_reporting(reports_dir: Path) -> CriterionResult:
    """I3: best overall + grid summary exist."""
    path_best = reports_dir / REFUSAL_OPT_BEST_JSON
    path_grid = reports_dir / REFUSAL_OPT_GRID_CSV
    best_exists = path_best.exists()
    grid_exists = path_grid.exists()
    pass_ = best_exists and grid_exists
    details: Dict[str, Any] = {"best_overall_exists": best_exists, "grid_summary_exists": grid_exists}
    if not pass_:
        details["reason"] = "one or both I3 artifacts missing"
    return CriterionResult("REFUSAL_OPT_REPORTING", pass_, details)


def evaluate_graduation(
    reports_dir: str | Path,
    *,
    delta_coverage_min: int = DEFAULT_DELTA_COVERAGE_MIN_FIXTURES,
    delta_payload_match_min: float = DEFAULT_DELTA_PAYLOAD_MATCH_MIN_RATE,
    staleness_min_reason_codes: int = DEFAULT_STALENESS_MIN_REASON_CODES,
    decay_min_reason_codes: int = DEFAULT_DECAY_MIN_REASON_CODES,
    uncertainty_min_decisions: int = DEFAULT_UNCERTAINTY_MIN_DECISIONS,
    worst_case_min_rows: int = DEFAULT_WORST_CASE_MIN_ROWS,
) -> GraduationResult:
    """
    Evaluate all graduation criteria from artifacts under reports_dir.
    Returns GraduationResult with criteria in deterministic order; overall_pass = AND of all passes.
    """
    reports_path = Path(reports_dir)
    computed_at = datetime.now(timezone.utc)
    if computed_at.tzinfo is None:
        computed_at = computed_at.replace(tzinfo=timezone.utc)

    results: List[CriterionResult] = []
    results.append(_check_delta_coverage(reports_path, delta_coverage_min))
    results.append(_check_delta_payload_match_rate(reports_path, delta_payload_match_min))
    results.append(_check_staleness_observability(reports_path, staleness_min_reason_codes))
    results.append(_check_decay_model_coverage(reports_path, decay_min_reason_codes))
    results.append(_check_uncertainty_signal_availability(reports_path, uncertainty_min_decisions))
    results.append(_check_late_data_robustness(reports_path))
    results.append(_check_worst_case_visibility(reports_path, worst_case_min_rows))
    results.append(_check_refusal_opt_reporting(reports_path))

    # Enforce deterministic order (already added in order)
    name_to_result = {r.name: r for r in results}
    ordered = [name_to_result[n] for n in CRITERION_ORDER if n in name_to_result]
    overall_pass = all(r.pass_ for r in ordered)

    return GraduationResult(overall_pass=overall_pass, criteria=ordered, computed_at_utc=computed_at)
