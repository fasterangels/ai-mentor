"""
Reason co-activation and conflict metrics (metrics-only; no decision/analyzer changes).

A reason is "active" for a decision if it appears in the decision's reason codes list.
Computes co-activation matrix (reason_i, reason_j) and conflict counts (opposite polarity in same decision).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

REASON_METRICS_VERSION = 1

# Minimal polarity map for known reason codes: support / oppose / neutral.
# Opposite polarity (support vs oppose) in same decision = conflict. Unknown -> neutral (no conflict).
POLARITY_SUPPORT = "support"
POLARITY_OPPOSE = "oppose"
POLARITY_NEUTRAL = "neutral"

DEFAULT_TOP_CONFLICT_PAIRS = 10

# Config: reason_code -> support | oppose | neutral (only non-neutral need be listed for conflicts)
REASON_POLARITY: Dict[str, str] = {
    "EXPECTED_GOALS_ABOVE": POLARITY_SUPPORT,
    "EXPECTED_GOALS_BELOW": POLARITY_OPPOSE,
    # Add more as needed; default is neutral
}


def _polarity(code: str) -> str:
    return REASON_POLARITY.get(code, POLARITY_NEUTRAL)


def _sort_dict_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with sorted keys for deterministic JSON."""
    if not isinstance(d, dict):
        return d
    return {k: _sort_dict_keys(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


def _coactivation_matrix_from_decisions(
    decisions: List[Tuple[str, List[str]]],
) -> Tuple[Dict[str, Dict[str, int]], Dict[str, Dict[str, Dict[str, int]]]]:
    """
    decisions: list of (market, reason_codes).
    Returns (global_matrix, per_market_matrices).
    Matrix is dict[reason_i][reason_j] = count (including diagonal = total activations for reason_i).
    """
    global_mat: Dict[str, Dict[str, int]] = {}
    per_market: Dict[str, Dict[str, Dict[str, int]]] = {}

    def ensure_matrix(mat: Dict[str, Dict[str, int]], ri: str, rj: str) -> None:
        if ri not in mat:
            mat[ri] = {}
        if rj not in mat[ri]:
            mat[ri][rj] = 0
        mat[ri][rj] += 1

    for market, codes in decisions:
        active = [c for c in codes if c]
        if not active:
            continue
        if market not in per_market:
            per_market[market] = {}
        for i, ri in enumerate(active):
            for rj in active[i:]:  # include diagonal and upper triangle
                ensure_matrix(global_mat, ri, rj)
                ensure_matrix(per_market[market], ri, rj)
                if ri != rj:
                    ensure_matrix(global_mat, rj, ri)
                    ensure_matrix(per_market[market], rj, ri)

    return global_mat, per_market


def _conflicts_from_decisions(
    decisions: List[Tuple[str, List[str]]],
    top_n: int = DEFAULT_TOP_CONFLICT_PAIRS,
) -> Tuple[int, float, List[Tuple[str, str, int]], Dict[str, Dict[str, Any]]]:
    """
    For each decision, count conflicts = pairs of active reasons with opposite polarity.
    Returns (global_conflict_count, global_conflict_rate, top_pairs_list, per_market_conflicts).
    top_pairs_list: [(reason_a, reason_b, count), ...] sorted by count desc.
    per_market_conflicts: market -> { conflict_count, conflict_rate, top_pairs }.
    """
    global_conflicts = 0
    pair_counts: Dict[Tuple[str, str], int] = {}
    per_market_data: Dict[str, Dict[str, Any]] = {}

    for market, codes in decisions:
        active = [c for c in codes if c]
        if market not in per_market_data:
            per_market_data[market] = {"conflict_count": 0, "decision_count": 0, "pair_counts": {}}
        per_market_data[market]["decision_count"] += 1

        for i, a in enumerate(active):
            for b in active[i + 1 :]:  # distinct pairs only
                pa, pb = _polarity(a), _polarity(b)
                if (pa, pb) in ((POLARITY_SUPPORT, POLARITY_OPPOSE), (POLARITY_OPPOSE, POLARITY_SUPPORT)):
                    global_conflicts += 1
                    per_market_data[market]["conflict_count"] += 1
                    key = (min(a, b), max(a, b))
                    pair_counts[key] = pair_counts.get(key, 0) + 1
                    per_market_data[market]["pair_counts"][key] = per_market_data[market]["pair_counts"].get(key, 0) + 1

    total_decisions = len(decisions)
    global_rate = (global_conflicts / total_decisions) if total_decisions else 0.0

    top_pairs = sorted(pair_counts.items(), key=lambda x: -x[1])[:top_n]
    top_pairs_list = [(a, b, c) for (a, b), c in top_pairs]

    per_market_out = {}
    for m, data in per_market_data.items():
        dc = data["decision_count"]
        cc = data["conflict_count"]
        rate = (cc / dc) if dc else 0.0
        top_m = sorted(data["pair_counts"].items(), key=lambda x: -x[1])[:top_n]
        per_market_out[m] = {
            "conflict_count": cc,
            "conflict_rate": round(rate, 4),
            "decision_count": dc,
            "top_pairs": [{"reason_a": a, "reason_b": b, "count": c} for (a, b), c in top_m],
        }

    return global_conflicts, round(global_rate, 4), top_pairs_list, per_market_out


def compute_reason_metrics(
    decisions: List[Tuple[str, List[str]]],
    top_conflict_pairs: int = DEFAULT_TOP_CONFLICT_PAIRS,
) -> Dict[str, Any]:
    """
    Compute co-activation and conflict metrics from a list of (market, reason_codes).

    decisions: list of (market, list of reason codes) per decision (e.g. per resolution per market).
    Returns dict with coactivation (global + per_market) and conflicts (global + per_market),
    suitable for JSON with deterministic key order.
    """
    if not decisions:
        return {
            "coactivation": {"global": {}, "per_market": {}},
            "conflicts": {
                "global": {"conflict_count": 0, "conflict_rate": 0.0, "decision_count": 0, "top_pairs": []},
                "per_market": {},
            },
        }

    global_mat, per_market_mat = _coactivation_matrix_from_decisions(decisions)
    global_conflict_count, global_conflict_rate, top_pairs_list, per_market_conflicts = _conflicts_from_decisions(
        decisions, top_n=top_conflict_pairs
    )

    coactivation = {
        "global": _sort_dict_keys({k: _sort_dict_keys(v) for k, v in sorted(global_mat.items())}),
        "per_market": _sort_dict_keys(
            {m: _sort_dict_keys({k: _sort_dict_keys(v) for k, v in sorted(mat.items())}) for m, mat in sorted(per_market_mat.items())}
        ),
    }

    conflicts = {
        "global": {
            "conflict_count": global_conflict_count,
            "conflict_rate": global_conflict_rate,
            "decision_count": len(decisions),
            "top_pairs": [{"reason_a": a, "reason_b": b, "count": c} for a, b, c in top_pairs_list],
        },
        "per_market": _sort_dict_keys(per_market_conflicts),
    }

    return {"coactivation": coactivation, "conflicts": conflicts}


def reason_metrics_for_report(
    decisions: List[Tuple[str, List[str]]],
    top_conflict_pairs: int = DEFAULT_TOP_CONFLICT_PAIRS,
) -> Dict[str, Any]:
    """
    Return the reason_metrics block and meta.reason_metrics_version for the evaluation report.
    """
    metrics = compute_reason_metrics(decisions, top_conflict_pairs=top_conflict_pairs)
    return {
        "reason_metrics": metrics,
        "meta": {"reason_metrics_version": REASON_METRICS_VERSION},
    }

