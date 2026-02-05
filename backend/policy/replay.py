"""
Replay regression: run analyzer with current vs proposed policy on same snapshots;
compare predictions and confidence; produce PASS/FAIL report.
"""

from __future__ import annotations

from typing import Any

from policy.policy_model import Policy
from policy.policy_runtime import min_confidence_from_policy
from policy.policy_store import checksum_report

# Avoid circular import by lazy imports for analyzer
MARKETS_V2 = ["1X2", "OU_2.5", "BTTS"]


def run_replay(
    snapshots: list[dict[str, Any]],
    current_policy: Policy,
    proposed_policy: Policy,
) -> dict[str, Any]:
    """
    Run analyzer twice per snapshot (current vs proposed policy).
    Compare prediction counts and confidence; return replay_report with PASS/FAIL.
    snapshots: list of { "match_id": str, "evidence_pack": dict } (evidence_pack serialized).
    """
    from evaluation.evaluation_v2 import evidence_pack_from_dict
    from analyzer.v2.engine import analyze_v2

    min_current = min_confidence_from_policy(current_policy)
    min_proposed = min_confidence_from_policy(proposed_policy)

    current_counts: dict[str, int] = {}
    proposed_counts: dict[str, int] = {}
    current_confidences: list[float] = []
    proposed_confidences: list[float] = []

    for item in snapshots:
        match_id = item.get("match_id") or "unknown"
        ep_dict = item.get("evidence_pack")
        if not ep_dict:
            continue
        try:
            ep = evidence_pack_from_dict(ep_dict)
        except Exception:
            continue
        out_current = analyze_v2("RESOLVED", ep, MARKETS_V2, min_confidence=min_current)
        out_proposed = analyze_v2("RESOLVED", ep, MARKETS_V2, min_confidence=min_proposed)

        for d in out_current.get("decisions") or []:
            m = d.get("market") or "?"
            current_counts[m] = current_counts.get(m, 0) + 1
            dec = d.get("decision")
            if dec == "PLAY":
                c = d.get("confidence")
                if c is not None:
                    current_confidences.append(float(c))
        for d in out_proposed.get("decisions") or []:
            m = d.get("market") or "?"
            proposed_counts[m] = proposed_counts.get(m, 0) + 1
            dec = d.get("decision")
            if dec == "PLAY":
                c = d.get("confidence")
                if c is not None:
                    proposed_confidences.append(float(c))

    # Predictions vs NO_PREDICTION: total PLAY decisions across all snapshots/markets
    n = len(snapshots)
    current_play = len(current_confidences)
    proposed_play = len(proposed_confidences)
    # Coverage = share of snapshots that got at least one PLAY (we don't have per-snapshot PLAY count here easily)
    # So use total PLAY count as proxy: if proposed_play drops more than 10% vs current_play, FAIL
    coverage_current = (current_play / (n * len(MARKETS_V2))) * 100.0 if n else 0.0
    coverage_proposed = (proposed_play / (n * len(MARKETS_V2))) * 100.0 if n else 0.0
    coverage_drop_pct = coverage_current - coverage_proposed if coverage_current else 0.0

    COVERAGE_DROP_THRESHOLD_PCT = 10.0
    passed = coverage_drop_pct <= COVERAGE_DROP_THRESHOLD_PCT

    # Input checksum for reproducibility
    snapshots_checksum = checksum_report({"snapshots_count": len(snapshots), "match_ids": [s.get("match_id") for s in snapshots]})

    report = {
        "replay_result": "PASS" if passed else "FAIL",
        "guardrails": {
            "coverage_drop_pct": round(coverage_drop_pct, 2),
            "coverage_drop_threshold_pct": COVERAGE_DROP_THRESHOLD_PCT,
            "passed": passed,
        },
        "current_policy_min_confidence": min_current,
        "proposed_policy_min_confidence": min_proposed,
        "snapshots_count": n,
        "current_play_count": current_play,
        "proposed_play_count": proposed_play,
        "current_coverage_pct": round(coverage_current, 2),
        "proposed_coverage_pct": round(coverage_proposed, 2),
        "current_counts_by_market": current_counts,
        "proposed_counts_by_market": proposed_counts,
        "confidence_delta_summary": {
            "current_mean": round(sum(current_confidences) / len(current_confidences), 4) if current_confidences else None,
            "proposed_mean": round(sum(proposed_confidences) / len(proposed_confidences), 4) if proposed_confidences else None,
        },
        "snapshots_checksum": snapshots_checksum,
    }
    return report
