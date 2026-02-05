"""
Canonical reason codes for analyzer v2 explain output (shadow/explain only).
New codes are additive; do not remove or rename existing ones.
"""

from __future__ import annotations

# Existing / inferred from current reason text
H2H_USED = "H2H_USED"
TOP_SEP = "TOP_SEP"
MISSING_STATS = "MISSING_STATS"
XG_PROXY = "XG_PROXY"
EXPECTED_GOALS_ABOVE = "EXPECTED_GOALS_ABOVE"
EXPECTED_GOALS_BELOW = "EXPECTED_GOALS_BELOW"
BTTS_TREND = "BTTS_TREND"
DEFENSIVE_STRENGTH = "DEFENSIVE_STRENGTH"
GATE_BLOCKED = "GATE_BLOCKED"

# Phase E: extended reason codes (shadow explainability)
FORM_RECENCY = "FORM_RECENCY"
HOME_AWAY_SPLIT = "HOME_AWAY_SPLIT"
GOALS_TREND = "GOALS_TREND"
DEFENSE_STABILITY = "DEFENSE_STABILITY"
MARKET_CONSENSUS_DAMPEN = "MARKET_CONSENSUS_DAMPEN"

# All known codes (for validation and reports)
ALL_REASON_CODES = frozenset({
    H2H_USED, TOP_SEP, MISSING_STATS, XG_PROXY,
    EXPECTED_GOALS_ABOVE, EXPECTED_GOALS_BELOW, BTTS_TREND, DEFENSIVE_STRENGTH, GATE_BLOCKED,
    FORM_RECENCY, HOME_AWAY_SPLIT, GOALS_TREND, DEFENSE_STABILITY, MARKET_CONSENSUS_DAMPEN,
})


def reason_entry(code: str, text: str) -> dict:
    """Build a single reason entry with code and text (for explain output)."""
    return {"code": code, "text": text}


def codes_for_reasons(reasons: list) -> list:
    """
    Map list of reason strings to list of codes (order preserved).
    Uses heuristics when no explicit code; returns same length as reasons.
    """
    out = []
    for r in reasons:
        if isinstance(r, dict):
            out.append(r.get("code") or r.get("text") or "UNKNOWN")
            continue
        s = (r or "").strip()
        if "H2H" in s or "h2h" in s.lower():
            out.append(H2H_USED)
        elif "top=" in s or "sep=" in s:
            out.append(TOP_SEP)
        elif "Missing stats" in s:
            out.append(MISSING_STATS)
        elif "xG proxy" in s or "expected goals" in s.lower():
            if "above" in s.lower():
                out.append(EXPECTED_GOALS_ABOVE)
            elif "below" in s.lower():
                out.append(EXPECTED_GOALS_BELOW)
            else:
                out.append(XG_PROXY)
        elif "both teams scoring" in s.lower() or "P(GG)" in s:
            out.append(BTTS_TREND)
        elif "defensive" in s.lower():
            out.append(DEFENSIVE_STRENGTH)
        elif "Gate blocked" in s:
            out.append(GATE_BLOCKED)
        else:
            out.append("UNKNOWN")
    return out
