"""Analyzer v2 — Quality gates (hard and soft).

Hard gates => NO_PREDICTION. Soft gates => NO_BET.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .contracts import (
    CONFLICT_T1_BLOCK,
    CONFLICT_T2_DOWNGRADE,
    GateId,
    MarketFlag,
    MAX_MINOR_FLAGS_BEFORE_NO_BET,
    OVERRIDE_CONFIDENCE_WHEN_BELOW_T2,
    SUPPORTED_MARKETS_V2,
    THRESHOLD_EVIDENCE_QUALITY,
)
from .features import consensus_quality_from_features, evidence_quality_score

# Type for one gate result (serializable)
GateResult = Dict[str, Any]  # gate_id, pass, notes


def run_hard_gates(
    resolver_status: str,
    market: str,
    features: Dict[str, Any],
) -> Tuple[bool, List[GateResult], List[str]]:
    """
    Run hard gates for a market. Returns (blocked, gate_results, flags).
    If blocked is True, decision must be NO_PREDICTION with returned flags.
    """
    gate_results: List[GateResult] = []
    flags: List[str] = []

    # 1) Resolver not RESOLVED => global; caller handles (no market-level gate here for resolver)
    if resolver_status != "RESOLVED":
        gate_results.append({
            "gate_id": GateId.RESOLVER,
            "pass": False,
            "notes": f"resolver status {resolver_status}",
        })
        flags.append(
            MarketFlag.AMBIGUOUS if resolver_status == "AMBIGUOUS" else MarketFlag.NOT_FOUND
        )
        return True, gate_results, flags

    gate_results.append({"gate_id": GateId.RESOLVER, "pass": True, "notes": "RESOLVED"})

    # 2) Market supported
    if market not in SUPPORTED_MARKETS_V2:
        gate_results.append({
            "gate_id": GateId.MARKET_SUPPORTED,
            "pass": False,
            "notes": f"market {market} not supported in v2",
        })
        flags.append(MarketFlag.MARKET_NOT_SUPPORTED)
        return True, gate_results, flags

    gate_results.append({"gate_id": GateId.MARKET_SUPPORTED, "pass": True, "notes": "supported"})

    # 3) Missing key features for this market
    missing = features.get("missing") or []
    required = _required_domains_for_market(market)
    if any(m in missing for m in required):
        gate_results.append({
            "gate_id": GateId.MISSING_KEY_FEATURES,
            "pass": False,
            "notes": f"missing domains: {[m for m in required if m in missing]}",
        })
        flags.append(MarketFlag.MISSING_KEY_FEATURES)
        return True, gate_results, flags

    gate_results.append({"gate_id": GateId.MISSING_KEY_FEATURES, "pass": True, "notes": "present"})

    # 4) Evidence quality
    eq_score = evidence_quality_score(features)
    if eq_score < THRESHOLD_EVIDENCE_QUALITY:
        gate_results.append({
            "gate_id": GateId.EVIDENCE_QUALITY,
            "pass": False,
            "notes": f"quality {eq_score:.2f} < {THRESHOLD_EVIDENCE_QUALITY}",
        })
        flags.append(MarketFlag.LOW_QUALITY_EVIDENCE)
        return True, gate_results, flags

    gate_results.append({
        "gate_id": GateId.EVIDENCE_QUALITY,
        "pass": True,
        "notes": f"quality {eq_score:.2f}",
    })

    # 5) Conflict / consensus quality
    cq = consensus_quality_from_features(features)
    if cq < CONFLICT_T1_BLOCK:
        gate_results.append({
            "gate_id": GateId.SOURCE_CONFLICT,
            "pass": False,
            "notes": f"consensus_quality {cq:.2f} < T1 {CONFLICT_T1_BLOCK}",
        })
        flags.append(MarketFlag.SOURCE_CONFLICT)
        return True, gate_results, flags

    if cq < CONFLICT_T2_DOWNGRADE:
        gate_results.append({
            "gate_id": GateId.SOURCE_CONFLICT,
            "pass": True,
            "notes": f"consensus_quality {cq:.2f} in [T1,T2); soft downgrade possible",
        })
        flags.append(MarketFlag.CONSENSUS_WEAK)
    else:
        gate_results.append({
            "gate_id": GateId.SOURCE_CONFLICT,
            "pass": True,
            "notes": f"consensus_quality {cq:.2f}",
        })

    return False, gate_results, flags


def _required_domains_for_market(market: str) -> List[str]:
    """Domains required for this market (e.g. stats for 1X2/OU/BTTS)."""
    if market in SUPPORTED_MARKETS_V2:
        return ["stats"]
    return ["stats"]


def should_downgrade_to_no_bet(
    confidence: float,
    minor_flags_count: int,
    consensus_quality: float,
    min_confidence: float = 0.62,
) -> Tuple[bool, List[GateResult]]:
    """
    Soft gates: borderline confidence or too many minor flags => NO_BET.
    When consensus_quality in [T1, T2), allow PLAY only if confidence >= override.
    Returns (downgrade, gate_results).
    """
    gate_results: List[GateResult] = []

    # Borderline confidence
    if confidence < min_confidence:
        gate_results.append({
            "gate_id": GateId.SOFT_BORDERLINE_CONFIDENCE,
            "pass": False,
            "notes": f"confidence {confidence:.2f} < min {min_confidence}",
        })
        return True, gate_results

    if consensus_quality < CONFLICT_T2_DOWNGRADE and confidence < OVERRIDE_CONFIDENCE_WHEN_BELOW_T2:
        gate_results.append({
            "gate_id": GateId.SOFT_BORDERLINE_CONFIDENCE,
            "pass": False,
            "notes": f"consensus below T2 and confidence {confidence:.2f} < override",
        })
        return True, gate_results

    gate_results.append({
        "gate_id": GateId.SOFT_BORDERLINE_CONFIDENCE,
        "pass": True,
        "notes": "confidence above threshold",
    })

    # Too many minor flags
    if minor_flags_count >= MAX_MINOR_FLAGS_BEFORE_NO_BET:
        gate_results.append({
            "gate_id": GateId.SOFT_MINOR_FLAGS,
            "pass": False,
            "notes": f"minor flags count {minor_flags_count} >= {MAX_MINOR_FLAGS_BEFORE_NO_BET}",
        })
        return True, gate_results

    gate_results.append({
        "gate_id": GateId.SOFT_MINOR_FLAGS,
        "pass": True,
        "notes": "minor flags within limit",
    })

    return False, gate_results
