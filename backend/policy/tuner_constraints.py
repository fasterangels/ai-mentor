"""
Shadow tuner constraints: drift budgets, hard caps, freeze params.
Applied to proposals only; deterministic. Does not apply changes automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Default constraint values (conservative)
DEFAULT_PER_PARAM_STEP_MAX = 0.01
DEFAULT_PER_RUN_TOTAL_DELTA_MAX = 0.03
DEFAULT_DRIFT_BUDGET_PER_MARKET = 0.02
DEFAULT_DRIFT_BUDGET_THRESHOLDS = 0.03
DEFAULT_DRIFT_BUDGET_DAMPENING = 0.05

MARKETS_ORDER = ("one_x_two", "over_under_25", "gg_ng")
MAX_TOP_DELTAS = 5


@dataclass
class TunerConstraintsConfig:
    """Tuner constraints (backward-compatible; all optional with safe defaults)."""
    drift_budgets: Dict[str, Any] = field(default_factory=lambda: {
        "per_market": {"one_x_two": DEFAULT_DRIFT_BUDGET_PER_MARKET, "over_under_25": DEFAULT_DRIFT_BUDGET_PER_MARKET, "gg_ng": DEFAULT_DRIFT_BUDGET_PER_MARKET},
        "per_param_group": {"thresholds": DEFAULT_DRIFT_BUDGET_THRESHOLDS, "dampening": DEFAULT_DRIFT_BUDGET_DAMPENING},
    })
    hard_caps: Dict[str, float] = field(default_factory=lambda: {
        "per_param_step_max": DEFAULT_PER_PARAM_STEP_MAX,
        "per_run_total_delta_max": DEFAULT_PER_RUN_TOTAL_DELTA_MAX,
    })
    freeze_params: List[str] = field(default_factory=list)


def get_tuner_constraints() -> TunerConstraintsConfig:
    """Return tuner constraints (defaults; optional future: load from JSON/env)."""
    return TunerConstraintsConfig()


def _path_market(path: str) -> Optional[str]:
    """Extract market key from path e.g. markets.one_x_two.min_confidence -> one_x_two."""
    if not path.startswith("markets."):
        return None
    parts = path.split(".")
    if len(parts) >= 2:
        return parts[1]
    return None


def _path_param_group(path: str) -> str:
    """Return param group: thresholds (min_confidence) or dampening."""
    if "min_confidence" in path:
        return "thresholds"
    if "dampening_factor" in path:
        return "dampening"
    return "other"


def apply_constraints(
    current_markets: Dict[str, Any],
    current_reasons: Dict[str, Any],
    diffs: List[Tuple[str, Any, Any, str]],
    config: Optional[TunerConstraintsConfig] = None,
) -> Tuple[List[Tuple[str, Any, Any, str]], Dict[str, Any]]:
    """
    Apply drift budgets and hard caps to diffs. Deterministic (sort by path).
    Returns (constrained_diffs, tuner_constraints_summary).
    """
    config = config or get_tuner_constraints()
    step_max = config.hard_caps.get("per_param_step_max", DEFAULT_PER_PARAM_STEP_MAX)
    total_max = config.hard_caps.get("per_run_total_delta_max", DEFAULT_PER_RUN_TOTAL_DELTA_MAX)
    per_market_budget = (config.drift_budgets.get("per_market") or {})
    per_group_budget = (config.drift_budgets.get("per_param_group") or {})
    freeze = set(config.freeze_params or [])

    # Build (path, old_val, new_val, reason, delta)
    items: List[Tuple[str, Any, Any, str, float]] = []
    for path, old_val, new_val, reason in diffs:
        if path in freeze:
            items.append((path, old_val, old_val, reason, 0.0))
            continue
        try:
            old_f = float(old_val)
            new_f = float(new_val)
            delta = new_f - old_f
        except (TypeError, ValueError):
            items.append((path, old_val, new_val, reason, 0.0))
            continue
        items.append((path, old_val, new_val, reason, delta))

    # Sort by path for determinism
    items.sort(key=lambda x: x[0])

    # 1) Per-parameter step cap
    clamped_count = 0
    for i, (path, old_val, new_val, reason, delta) in enumerate(items):
        if path in freeze:
            continue
        try:
            old_f = float(old_val)
            delta = float(items[i][4])
        except (TypeError, ValueError):
            continue
        capped = max(-step_max, min(step_max, delta))
        if capped != delta:
            clamped_count += 1
        new_f = old_f + capped
        items[i] = (path, old_val, new_f, reason, capped)

    # 2) Per-run total delta cap
    total_abs = sum(abs(it[4]) for it in items)
    scaled_down = False
    if total_abs > total_max and total_abs > 0:
        scale = total_max / total_abs
        scaled_down = True
        for i in range(len(items)):
            path, old_val, new_val, reason, delta = items[i]
            if path in freeze:
                continue
            new_delta = delta * scale
            try:
                old_f = float(old_val)
                items[i] = (path, old_val, old_f + new_delta, reason, new_delta)
            except (TypeError, ValueError):
                pass

    # 3) Drift budgets: per market and per param_group
    def _scale_group(indices: List[int], budget: float) -> None:
        group_abs = sum(abs(items[j][4]) for j in indices)
        if group_abs <= budget or group_abs <= 0:
            return
        scale = budget / group_abs
        for j in indices:
            path, old_val, new_val, reason, delta = items[j]
            if path in freeze:
                continue
            new_delta = delta * scale
            try:
                old_f = float(old_val)
                items[j] = (path, old_val, old_f + new_delta, reason, new_delta)
            except (TypeError, ValueError):
                pass

    by_market: Dict[str, List[int]] = {}
    by_group: Dict[str, List[int]] = {}
    for i, (path, _, _, _, _) in enumerate(items):
        m = _path_market(path)
        if m:
            by_market.setdefault(m, []).append(i)
        g = _path_param_group(path)
        by_group.setdefault(g, []).append(i)

    for m in MARKETS_ORDER:
        budget = per_market_budget.get(m)
        if budget is not None and m in by_market:
            _scale_group(by_market[m], float(budget))
    for g in ("thresholds", "dampening"):
        budget = per_group_budget.get(g)
        if budget is not None and g in by_group:
            _scale_group(by_group[g], float(budget))

    constrained_diffs = [(path, old_val, new_val, reason) for path, old_val, new_val, reason, _ in items]

    # Summary: budgets used, caps applied, scaled_down, clamped_count, top 5 deltas
    deltas_with_path = [(it[0], it[4]) for it in items if it[4] != 0]
    deltas_with_path.sort(key=lambda x: -abs(x[1]))
    top_deltas = [(path, round(delta, 4)) for path, delta in deltas_with_path[:MAX_TOP_DELTAS]]

    summary = {
        "budgets_used": True,
        "caps_applied": True,
        "scaled_down": scaled_down,
        "clamped_params_count": clamped_count,
        "top_deltas": top_deltas,
    }
    return constrained_diffs, summary
