"""Analyzer v2 — Market-specific scoring (1X2, OU_2.5, BTTS)."""

from __future__ import annotations

from typing import Any, Callable, Dict

from ..contracts import MARKET_1X2, MARKET_BTTS, MARKET_OU_25

from .market_1x2 import score_1x2
from .market_ou_25 import score_ou_25
from .market_btts import score_btts

# market_id -> (features, gate_results, consensus_quality, min_confidence) -> decision_dict
SCORERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    MARKET_1X2: score_1x2,
    MARKET_OU_25: score_ou_25,
    MARKET_BTTS: score_btts,
}


def score_market(
    market: str,
    features: Dict[str, Any],
    gate_results: list,
    consensus_quality: float,
    min_confidence: float = 0.62,
) -> Dict[str, Any]:
    """Dispatch to market scorer; return v2 decision dict."""
    fn = SCORERS.get(market)
    if not fn:
        return _unsupported_market_decision(market)
    return fn(features, gate_results, consensus_quality, min_confidence)


def _unsupported_market_decision(market: str) -> Dict[str, Any]:
    from ..contracts import (
        MAX_DECISION_REASONS,
        POLICY_VERSION_V2,
        DecisionKind,
        MarketFlag,
    )
    return {
        "market": market,
        "decision": DecisionKind.NO_PREDICTION,
        "selection": None,
        "confidence": None,
        "reasons": ["Market not supported in v2"],
        "flags": [MarketFlag.MARKET_NOT_SUPPORTED],
        "evidence_refs": [],
        "policy_version": POLICY_VERSION_V2,
        "meta": {},
    }
