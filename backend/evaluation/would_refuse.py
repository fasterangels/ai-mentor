"""
Shadow-only "would-refuse" simulator (metrics-only; no analyzer behavior changes).

For each evaluated decision, determines whether we *would* have refused
under a simple ruleset, and aggregates global + per-market metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from evaluation.reason_metrics import (  # reuse polarity map
    POLARITY_NEUTRAL,
    POLARITY_OPPOSE,
    POLARITY_SUPPORT,
    REASON_POLARITY,
)


WOULD_REFUSE_VERSION = 1

R1_ID = "R1_low_confidence"
R2_ID = "R2_reason_conflict"
R3_ID = "R3_low_reliability"
R4_ID = "R4_sparse_evidence"

DEFAULT_LOW_CONF_THRESHOLD = 0.55
DEFAULT_RELIABILITY_THRESHOLD = 0.45


@dataclass
class DecisionRecord:
    market: str
    outcome: str  # "SUCCESS" | "FAILURE" | "NEUTRAL" | "UNRESOLVED"
    confidence: Optional[float]
    reason_codes: List[str]


def _polarity(code: str) -> str:
    return REASON_POLARITY.get(code, POLARITY_NEUTRAL)


def _reason_reliability_for(
    reason_reliability: Dict[str, Any] | None,
    reason: str,
    market: str,
) -> Optional[float]:
    if not reason_reliability:
        return None
    entry = reason_reliability.get(reason)
    if not isinstance(entry, dict):
        return None
    per_market = entry.get("per_market") or {}
    if market in per_market:
        return per_market[market].get("reliability")
    global_block = entry.get("global") or {}
    return global_block.get("reliability")


def simulate_would_refuse(
    decisions: List[DecisionRecord],
    reason_reliability: Dict[str, Any] | None = None,
    low_conf_threshold: float = DEFAULT_LOW_CONF_THRESHOLD,
    reliability_threshold: float = DEFAULT_RELIABILITY_THRESHOLD,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run shadow-only would-refuse simulation for a list of decisions.

    Returns:
      (per_decision_outputs, metrics_dict)

    per_decision_outputs: list of {
        "market": str,
        "outcome": str,
        "confidence": float | None,
        "reason_codes": [...],
        "would_refuse": bool,
        "would_refuse_reasons": [rule_ids...],
    }

    metrics_dict: {
      "global": { ... },
      "per_market": { market -> { ... } },
      "rules": {
        "global": { rule_id -> count },
        "per_market": { market -> { rule_id -> count } },
      },
      "params": { ... },
    }
    """
    per_decision: List[Dict[str, Any]] = []

    global_total = 0
    global_errors = 0
    global_correct = 0
    global_wr = 0
    global_wr_errors = 0
    global_wr_correct = 0

    per_market_counts: Dict[str, Dict[str, int]] = {}
    rule_global: Dict[str, int] = {}
    rule_per_market: Dict[str, Dict[str, int]] = {}

    for d in decisions:
        market = d.market
        outcome = d.outcome or ""
        conf = d.confidence
        codes = [c for c in d.reason_codes if c]

        is_error = outcome == "FAILURE"
        is_correct = outcome == "SUCCESS"

        global_total += 1
        if is_error:
            global_errors += 1
        if is_correct:
            global_correct += 1

        m_counts = per_market_counts.setdefault(
            market,
            {"total": 0, "errors": 0, "correct": 0, "wr": 0, "wr_errors": 0, "wr_correct": 0},
        )
        m_counts["total"] += 1
        if is_error:
            m_counts["errors"] += 1
        if is_correct:
            m_counts["correct"] += 1

        triggered: List[str] = []

        # R1: low confidence
        if conf is not None and conf < low_conf_threshold:
            triggered.append(R1_ID)

        # R2: reason conflict (support + oppose)
        pols = {_polarity(c) for c in codes}
        if POLARITY_SUPPORT in pols and POLARITY_OPPOSE in pols:
            triggered.append(R2_ID)

        # R3: low reliability reason active
        if reason_reliability:
            for code in codes:
                rr = _reason_reliability_for(reason_reliability, code, market)
                if rr is not None and rr < reliability_threshold:
                    triggered.append(R3_ID)
                    break

        # R4: sparse evidence
        if len(codes) <= 1:
            triggered.append(R4_ID)

        triggered = sorted(set(triggered))
        would_refuse = bool(triggered)

        if would_refuse:
            global_wr += 1
            m_counts["wr"] += 1
            if is_error:
                global_wr_errors += 1
                m_counts["wr_errors"] += 1
            if is_correct:
                global_wr_correct += 1
                m_counts["wr_correct"] += 1
            pm_rules = rule_per_market.setdefault(market, {})
            for rid in triggered:
                rule_global[rid] = rule_global.get(rid, 0) + 1
                pm_rules[rid] = pm_rules.get(rid, 0) + 1

        per_decision.append(
            {
                "market": market,
                "outcome": outcome,
                "confidence": conf,
                "reason_codes": list(codes),
                "would_refuse": would_refuse,
                "would_refuse_reasons": triggered,
            }
        )

    def _rate(num: int, denom: int) -> float:
        return round(num / denom, 6) if denom > 0 else 0.0

    global_metrics = {
        "total_decisions": global_total,
        "would_refuse_count": global_wr,
        "would_refuse_rate": _rate(global_wr, global_total),
        "errors_count": global_errors,
        "would_refuse_on_errors_count": global_wr_errors,
        "would_refuse_on_errors_rate": _rate(global_wr_errors, global_errors),
        "correct_count": global_correct,
        "would_refuse_on_correct_count": global_wr_correct,
        "would_refuse_on_correct_rate": _rate(global_wr_correct, global_correct),
    }

    per_market_metrics: Dict[str, Any] = {}
    for market in sorted(per_market_counts.keys()):
        c = per_market_counts[market]
        per_market_metrics[market] = {
            "total_decisions": c["total"],
            "would_refuse_count": c["wr"],
            "would_refuse_rate": _rate(c["wr"], c["total"]),
            "errors_count": c["errors"],
            "would_refuse_on_errors_count": c["wr_errors"],
            "would_refuse_on_errors_rate": _rate(c["wr_errors"], c["errors"]),
            "correct_count": c["correct"],
            "would_refuse_on_correct_count": c["wr_correct"],
            "would_refuse_on_correct_rate": _rate(c["wr_correct"], c["correct"]),
        }

    rules_block = {
        "global": {k: rule_global[k] for k in sorted(rule_global.keys())},
        "per_market": {
            m: {k: rule_per_market[m][k] for k in sorted(rule_per_market[m].keys())}
            for m in sorted(rule_per_market.keys())
        },
    }

    metrics = {
        "global": global_metrics,
        "per_market": per_market_metrics,
        "rules": rules_block,
        "params": {
            "low_conf_threshold": low_conf_threshold,
            "reliability_threshold": reliability_threshold,
        },
    }
    return per_decision, metrics


def would_refuse_for_report(
    decisions: List[DecisionRecord],
    reason_reliability: Dict[str, Any] | None = None,
    low_conf_threshold: float = DEFAULT_LOW_CONF_THRESHOLD,
    reliability_threshold: float = DEFAULT_RELIABILITY_THRESHOLD,
) -> Dict[str, Any]:
    """
    Wrap simulate_would_refuse with versioned meta for evaluation reports.
    """
    _, metrics = simulate_would_refuse(
        decisions,
        reason_reliability=reason_reliability,
        low_conf_threshold=low_conf_threshold,
        reliability_threshold=reliability_threshold,
    )
    return {
        "would_refuse_metrics": metrics,
        "meta": {"would_refuse_version": WOULD_REFUSE_VERSION},
    }

