"""
Tuner impact reporting: proposal diff (bounded) and per-market impact from eval + optional replay.
Deterministic, report-only; no production changes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

MARKETS_ORDER = ("one_x_two", "over_under_25", "gg_ng")
REPLAY_MARKET_TO_POLICY = {"1X2": "one_x_two", "OU_2.5": "over_under_25", "BTTS": "gg_ng"}
TOP_CHANGES_CAP = 10
IMPACT_ROUND = 4


def build_tuner_proposal_diff(
    current_version: str,
    proposed_version: str,
    diffs: List[Tuple[str, Any, Any, str]],
    constraints_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build bounded audit diff: policy versions, params_changed_count, top_changes (top 10 by |delta|), constraints_applied.
    Deterministic: top_changes sorted by abs(delta) descending then by path.
    """
    constraints_applied = dict(constraints_summary or {})

    # Compute numeric deltas for ordering; keep (path, old, new, delta)
    items: List[Tuple[str, Any, Any, float]] = []
    for path, old_val, new_val, _reason in diffs:
        try:
            delta = float(new_val) - float(old_val)
        except (TypeError, ValueError):
            delta = 0.0
        items.append((path, old_val, new_val, delta))

    # Deterministic: sort by abs(delta) desc, then path asc
    items.sort(key=lambda x: (-abs(x[3]), x[0]))
    top_changes = []
    for path, old_val, new_val, delta in items[:TOP_CHANGES_CAP]:
        top_changes.append({
            "param_path": path,
            "old_value": round(old_val, IMPACT_ROUND) if isinstance(old_val, (int, float)) else old_val,
            "new_value": round(new_val, IMPACT_ROUND) if isinstance(new_val, (int, float)) else new_val,
            "delta": round(delta, IMPACT_ROUND),
        })

    return {
        "policy_from_version": current_version,
        "policy_to_version": proposed_version,
        "params_changed_count": len(diffs),
        "top_changes": top_changes,
        "constraints_applied": constraints_applied,
    }


def build_tuner_impact_by_market(
    evaluation_report: Dict[str, Any],
    replay_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Build per-market impact table: from eval report (accuracy, neutrals, sample_size);
    if replay_report provided, add current_play_count, proposed_play_count, play_count_delta.
    Stable market ordering (MARKETS_ORDER). Round to IMPACT_ROUND decimals.
    """
    per_market = evaluation_report.get("per_market_accuracy") or {}
    result: Dict[str, Dict[str, Any]] = {}

    for market in MARKETS_ORDER:
        data = per_market.get(market) or {}
        s = data.get("success_count") or 0
        f = data.get("failure_count") or 0
        n = data.get("neutral_count") or 0
        sample_size = s + f + n
        accuracy = round(s / (s + f), IMPACT_ROUND) if (s + f) > 0 else None
        neutrals = n  # count; optional neutrals_rate = round(n / sample_size, IMPACT_ROUND) if sample_size else 0

        row: Dict[str, Any] = {
            "accuracy": accuracy,
            "neutrals": neutrals,
            "sample_size": sample_size,
        }

        if replay_report:
            current_by_market = replay_report.get("current_counts_by_market") or {}
            proposed_by_market = replay_report.get("proposed_counts_by_market") or {}
            # Replay uses 1X2, OU_2.5, BTTS
            rev_map = {v: k for k, v in REPLAY_MARKET_TO_POLICY.items()}
            replay_key = rev_map.get(market)
            if replay_key:
                cur = current_by_market.get(replay_key) or 0
                prop = proposed_by_market.get(replay_key) or 0
                row["current_play_count"] = cur
                row["proposed_play_count"] = prop
                row["play_count_delta"] = prop - cur

        result[market] = row

    return result
