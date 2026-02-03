"""
Reason attribution: for each resolved snapshot, emit (reason_code, market, outcome) per market.

Minimal viable: correlation tracking only; no causality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ReasonAttributionRow:
    """One row for the evaluator: reason_code, market, outcome."""

    reason_code: str
    market: str  # one_x_two | over_under_25 | gg_ng
    outcome: str  # SUCCESS | FAILURE | NEUTRAL | UNRESOLVED


def reason_codes_by_market_from_resolution(resolution: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract reason_codes_by_market from a resolution (dict or ORM-like with get)."""
    if hasattr(resolution, "get"):
        raw = resolution.get("reason_codes_by_market") or resolution.get("reason_codes_by_market_json")
    else:
        raw = getattr(resolution, "reason_codes_by_market_json", None)
    if raw is None:
        return {"one_x_two": [], "over_under_25": [], "gg_ng": []}
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return {"one_x_two": [], "over_under_25": [], "gg_ng": []}
    if not isinstance(raw, dict):
        return {"one_x_two": [], "over_under_25": [], "gg_ng": []}
    return {
        "one_x_two": list(raw.get("one_x_two") or []),
        "over_under_25": list(raw.get("over_under_25") or []),
        "gg_ng": list(raw.get("gg_ng") or []),
    }


def market_outcomes_from_resolution(resolution: Dict[str, Any]) -> Dict[str, str]:
    """Extract market_outcomes from a resolution (dict or ORM-like)."""
    if hasattr(resolution, "get"):
        raw = resolution.get("market_outcomes") or resolution.get("market_outcomes_json")
    else:
        raw = getattr(resolution, "market_outcomes_json", None)
    if raw is None:
        return {}
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return {}
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def emit_attribution_rows(
    reason_codes_by_market: Dict[str, List[str]],
    market_outcomes: Dict[str, str],
) -> List[ReasonAttributionRow]:
    """
    For each market and each reason_code in reason_codes_by_market[market], emit one row.

    outcome is taken from market_outcomes[market].
    """
    rows: List[ReasonAttributionRow] = []
    for market, codes in reason_codes_by_market.items():
        outcome = market_outcomes.get(market, "UNRESOLVED")
        for code in codes:
            if code:
                rows.append(
                    ReasonAttributionRow(
                        reason_code=str(code),
                        market=market,
                        outcome=outcome,
                    )
                )
    return rows
