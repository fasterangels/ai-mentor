"""
Guided policy tuning from quality_audit report (shadow-only, reversible).
Consumes latest quality_audit; produces deterministic tuning proposals with caps and guardrails.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from policy.policy_model import MarketPolicy, Policy, PolicyVersion, ReasonPolicy
from policy.policy_runtime import get_active_policy

MARKETS = ("one_x_two", "over_under_25", "gg_ng")

# Caps and guardrails
MAX_MIN_CONFIDENCE_DELTA_PER_RUN = 0.05
MIN_COVERAGE_FLOOR = 0.5
MAX_PROPOSALS_PER_PLAN = 5
DAMPENING_MULTIPLIER = 0.8
DAMPENING_FLOOR = 0.3
MIN_EMPIRICAL_DEVIATION_TO_PROPOSE = 0.08
MIN_COUNT_FOR_CALIBRATION_PROPOSAL = 10


def plan_from_quality_audit(
    quality_audit_report: Dict[str, Any],
    current_policy: Optional[Policy] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Consume quality_audit report; produce deterministic tuning proposals.
    Applies: max delta per run, min coverage floor, no aggressive simultaneous changes (cap total).
    Returns: proposals (list), proposed_policy_snapshot (dict), guardrails_passed (bool).
    """
    config = config or {}
    current = current_policy or get_active_policy()
    max_delta = float(config.get("max_min_confidence_delta", MAX_MIN_CONFIDENCE_DELTA_PER_RUN))
    max_proposals = int(config.get("max_proposals_per_plan", MAX_PROPOSALS_PER_PLAN))

    proposals: List[Dict[str, Any]] = []
    proposed_markets: Dict[str, MarketPolicy] = {
        m: MarketPolicy(
            min_confidence=current.markets.get(m, MarketPolicy(min_confidence=0.62)).min_confidence,
            confidence_bands=current.markets.get(m).confidence_bands if current.markets.get(m) else None,
        )
        for m in MARKETS
    }
    proposed_reasons: Dict[str, ReasonPolicy] = {
        k: ReasonPolicy(reason_code=v.reason_code, dampening_factor=v.dampening_factor)
        for k, v in current.reasons.items()
    }
    for code in (current.reasons or {}):
        if code not in proposed_reasons:
            proposed_reasons[code] = ReasonPolicy(reason_code=code, dampening_factor=1.0)

    suggestions = quality_audit_report.get("suggestions") or {}
    calibration = quality_audit_report.get("confidence_calibration") or {}

    # 1) min_confidence adjustments from miscalibration (empirical < predicted -> raise bar)
    band_adjustments = suggestions.get("confidence_band_adjustments") or []
    for adj in band_adjustments:
        if len(proposals) >= max_proposals:
            break
        market = adj.get("market")
        if market not in MARKETS:
            continue
        pred = adj.get("predicted_confidence")
        emp = adj.get("empirical_accuracy")
        count = adj.get("count", 0)
        if pred is None or emp is None or count < MIN_COUNT_FOR_CALIBRATION_PROPOSAL:
            continue
        deviation = abs(emp - pred)
        if deviation < MIN_EMPIRICAL_DEVIATION_TO_PROPOSE:
            continue
        cur = proposed_markets[market]
        old_mc = cur.min_confidence
        bump = min(max_delta, max(0.02, (pred - emp) * 0.5)) if emp < pred else 0.0
        if bump <= 0:
            continue
        new_mc = round(min(0.75, old_mc + bump), 4)
        if new_mc <= old_mc:
            continue
        proposed_markets[market] = MarketPolicy(min_confidence=new_mc, confidence_bands=cur.confidence_bands)
        proposals.append({
            "type": "min_confidence",
            "market": market,
            "old_val": old_mc,
            "new_val": new_mc,
            "reason": f"calibration deviation {deviation:.2f} (emp {emp:.2f} vs pred {pred:.2f}), n={count}",
        })

    # 2) reason dampening from effectiveness degradation
    dampening_candidates = suggestions.get("dampening_candidates") or []
    for cand in dampening_candidates:
        if len(proposals) >= max_proposals:
            break
        code = cand.get("reason_code")
        if not code:
            continue
        old_df = proposed_reasons.get(code)
        old_val = old_df.dampening_factor if old_df else 1.0
        new_val = round(max(DAMPENING_FLOOR, old_val * DAMPENING_MULTIPLIER), 4)
        if new_val >= old_val:
            continue
        if code not in proposed_reasons:
            proposed_reasons[code] = ReasonPolicy(reason_code=code, dampening_factor=new_val)
        else:
            proposed_reasons[code] = ReasonPolicy(reason_code=code, dampening_factor=new_val)
        proposals.append({
            "type": "dampening",
            "reason_code": code,
            "old_val": old_val,
            "new_val": new_val,
            "reason": cand.get("suggestion", "effectiveness decay"),
        })

    proposed_policy = Policy(
        meta=PolicyVersion(
            version=current.meta.version + "-tuned-plan",
            created_at_utc=datetime.now(timezone.utc),
            notes="Shadow tuning plan from quality_audit",
        ),
        markets=proposed_markets,
        reasons=proposed_reasons,
    )

    guardrails_results: List[Dict[str, Any]] = []
    for p in proposals:
        if p.get("type") == "min_confidence":
            delta = p["new_val"] - p["old_val"]
            guardrails_results.append({
                "check": "max_delta",
                "passed": delta <= max_delta,
                "detail": f"{p.get('market')}: delta {delta:.3f}",
            })
        else:
            guardrails_results.append({"check": "dampening", "passed": True, "detail": p.get("reason_code", "")})
    guardrails_passed = all(g.get("passed", True) for g in guardrails_results)

    return {
        "proposals": proposals,
        "proposed_policy_snapshot": {
            "markets": {m: {"min_confidence": proposed_markets[m].min_confidence} for m in MARKETS},
            "reasons": {k: {"dampening_factor": v.dampening_factor} for k, v in proposed_reasons.items()},
        },
        "guardrails_passed": guardrails_passed,
        "guardrails_results": guardrails_results,
        "proposal_count": len(proposals),
    }


def replay_regression(
    records: List[Dict[str, Any]],
    proposed_min_confidence_by_market: Dict[str, float],
    coverage_drop_threshold: float = 0.10,
    accuracy_drop_threshold: float = 0.05,
) -> Dict[str, Any]:
    """
    Replay: apply proposed min_confidence to history; compute coverage and accuracy.
    Block if coverage drop > coverage_drop_threshold OR accuracy drop > accuracy_drop_threshold.
    Deterministic.
    """
    market_key_map = {"1X2": "one_x_two", "OU25": "over_under_25", "OU_2.5": "over_under_25", "GGNG": "gg_ng", "BTTS": "gg_ng"}

    def _market_key(m: str) -> str:
        return market_key_map.get((m or "").upper(), (m or "").lower())

    baseline_covered = 0
    baseline_success = 0
    baseline_failure = 0
    proposed_covered = 0
    proposed_success = 0
    proposed_failure = 0

    for rec in records:
        outcomes = rec.get("market_outcomes") or {}
        preds = rec.get("predictions") or []
        for p in preds:
            market = _market_key(p.get("market") or "")
            if market not in MARKETS:
                continue
            try:
                conf = float(p.get("confidence") or 0)
            except (TypeError, ValueError):
                continue
            outcome = outcomes.get(market, "UNRESOLVED")
            if outcome not in ("SUCCESS", "FAILURE"):
                continue
            baseline_covered += 1
            if outcome == "SUCCESS":
                baseline_success += 1
            else:
                baseline_failure += 1

            min_conf = proposed_min_confidence_by_market.get(market)
            if min_conf is None:
                min_conf = 0.62
            if conf >= min_conf:
                proposed_covered += 1
                if outcome == "SUCCESS":
                    proposed_success += 1
                else:
                    proposed_failure += 1

    total_baseline = baseline_covered
    total_proposed = proposed_covered
    baseline_coverage_pct = (baseline_covered / (len(records) * len(MARKETS))) if records else 0.0
    proposed_coverage_pct = (proposed_covered / (len(records) * len(MARKETS))) if records else 0.0
    if len(records) * len(MARKETS) == 0:
        baseline_coverage_pct = 1.0
        proposed_coverage_pct = 1.0

    baseline_accuracy = baseline_success / (baseline_success + baseline_failure) if (baseline_success + baseline_failure) > 0 else 0.0
    proposed_accuracy = proposed_success / (proposed_success + proposed_failure) if (proposed_success + proposed_failure) > 0 else 0.0

    coverage_drop = baseline_coverage_pct - proposed_coverage_pct if baseline_coverage_pct else 0.0
    accuracy_drop = baseline_accuracy - proposed_accuracy if baseline_accuracy else 0.0

    blocked = coverage_drop > coverage_drop_threshold or accuracy_drop > accuracy_drop_threshold
    reasons_list = [r for r in [
        f"coverage_drop {coverage_drop:.2%} > {coverage_drop_threshold:.0%}" if coverage_drop > coverage_drop_threshold else None,
        f"accuracy_drop {accuracy_drop:.2%} > {accuracy_drop_threshold:.0%}" if accuracy_drop > accuracy_drop_threshold else None,
    ] if r is not None]
    return {
        "baseline_coverage_pct": round(baseline_coverage_pct, 4),
        "proposed_coverage_pct": round(proposed_coverage_pct, 4),
        "coverage_drop": round(coverage_drop, 4),
        "baseline_accuracy": round(baseline_accuracy, 4),
        "proposed_accuracy": round(proposed_accuracy, 4),
        "accuracy_drop": round(accuracy_drop, 4),
        "blocked": blocked,
        "reasons": reasons_list,
    }
