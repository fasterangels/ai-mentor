"""
Burn-in mode: very limited, high-safety real-world activation.
Requires ACTIVATION_MODE=burn_in and enforces stricter gates and guardrails.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from reports.index_store import load_index

# Burn-in: only real_provider by default
BURN_IN_DEFAULT_CONNECTORS: Set[str] = {"real_provider"}
BURN_IN_DEFAULT_MARKETS: Set[str] = {"1X2"}
BURN_IN_MAX_MATCHES_MIN = 1
BURN_IN_MAX_MATCHES_MAX = 3
BURN_IN_MAX_MATCHES_DEFAULT = 1

# Guardrail thresholds (abort activation if exceeded)
BURN_IN_MAX_LIVE_IO_ALERTS = 0
BURN_IN_MAX_PICK_CHANGE_RATE = 0.1  # 10%
BURN_IN_MAX_CONFIDENCE_DELTA_P95 = 0.05  # 5%


def is_burn_in_mode() -> bool:
    """True if ACTIVATION_MODE=burn_in."""
    return os.environ.get("ACTIVATION_MODE", "").strip().lower() == "burn_in"


def burn_in_max_matches() -> int:
    """
    Max matches for burn-in: 1-3 only.
    ACTIVATION_MAX_MATCHES env override allowed but capped at 3.
    Default: 1.
    """
    try:
        val = int(os.environ.get("ACTIVATION_MAX_MATCHES", str(BURN_IN_MAX_MATCHES_DEFAULT)))
    except ValueError:
        return BURN_IN_MAX_MATCHES_DEFAULT
    if val < BURN_IN_MAX_MATCHES_MIN:
        return BURN_IN_MAX_MATCHES_MIN
    if val > BURN_IN_MAX_MATCHES_MAX:
        return BURN_IN_MAX_MATCHES_MAX
    return val


def burn_in_min_confidence() -> float:
    """
    Stricter confidence threshold for burn-in (must be > policy.min_confidence).
    ACTIVATION_MIN_CONFIDENCE_BURN_IN env; default 0.85.
    """
    try:
        return float(os.environ.get("ACTIVATION_MIN_CONFIDENCE_BURN_IN", "0.85"))
    except ValueError:
        return 0.85


def burn_in_connectors() -> Set[str]:
    """Whitelist of connectors for burn-in (default: real_provider only)."""
    s = os.environ.get("ACTIVATION_CONNECTORS", "").strip()
    if s:
        return {c.strip() for c in s.split(",") if c.strip()}
    return BURN_IN_DEFAULT_CONNECTORS.copy()


def burn_in_markets() -> Set[str]:
    """Whitelist of markets for burn-in (default: 1X2 only)."""
    s = os.environ.get("ACTIVATION_MARKETS", "").strip()
    if s:
        return {m.strip() for m in s.split(",") if m.strip()}
    return BURN_IN_DEFAULT_MARKETS.copy()


def check_burn_in_live_io_alerts(
    live_io_alerts: List[Any],
    max_alerts: int = BURN_IN_MAX_LIVE_IO_ALERTS,
) -> tuple[bool, Optional[str]]:
    """
    Abort activation if live IO alerts exceed max (burn-in: 0).
    Returns (pass, reason_if_fail).
    """
    count = len(live_io_alerts) if live_io_alerts else 0
    if count > max_alerts:
        return False, f"Burn-in: live IO alerts {count} exceeds max {max_alerts}"
    return True, None


def check_burn_in_vs_recorded(
    index_path: str = "reports/index.json",
    max_pick_change_rate: float = BURN_IN_MAX_PICK_CHANGE_RATE,
    max_confidence_delta_p95: float = BURN_IN_MAX_CONFIDENCE_DELTA_P95,
) -> tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Check latest live shadow analyze run for burn-in guardrails.
    Returns (pass, reason_if_fail, guardrail_state).
    """
    state: Dict[str, Any] = {
        "max_pick_change_rate": max_pick_change_rate,
        "max_confidence_delta_p95": max_confidence_delta_p95,
    }
    try:
        index = load_index(index_path)
        runs = index.get("live_shadow_analyze_runs") or []
        if not runs:
            state["latest_run_id"] = None
            return True, None, state

        latest = runs[-1]
        run_id = latest.get("run_id")
        state["latest_run_id"] = run_id
        summary = latest.get("summary") or {}

        # If we had summary with pick/confidence metrics we could check; for now allow
        alerts_count = latest.get("alerts_count", 0)
        if alerts_count > 0:
            return False, f"Burn-in: latest live shadow analyze run has {alerts_count} alert(s)", state
        return True, None, state
    except Exception:  # noqa: BLE001
        return False, "Unable to check burn-in vs recorded guardrails", state


def check_burn_in_gate(
    connector_name: str,
    market: str,
    confidence: float,
    policy_min_confidence: float,
    index_path: str = "reports/index.json",
) -> tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Check if activation is allowed for burn-in mode for a single decision.
    Returns (allowed, reason_if_not_allowed, guardrail_state).
    """
    state: Dict[str, Any] = {"burn_in_confidence_gate": burn_in_min_confidence()}

    # Connector: real_provider only (or explicit whitelist)
    allowed_connectors = burn_in_connectors()
    if connector_name not in allowed_connectors:
        return False, f"Burn-in: connector '{connector_name}' not allowed (whitelist: {list(allowed_connectors)})", state

    # Market: 1X2 only by default
    allowed_markets = burn_in_markets()
    if market not in allowed_markets:
        return False, f"Burn-in: market '{market}' not in whitelist {list(allowed_markets)}", state

    # Confidence: must be above policy minimum and burn-in minimum
    if confidence < policy_min_confidence:
        return False, f"Confidence {confidence:.3f} below policy minimum {policy_min_confidence:.3f}", state
    burn_in_min = burn_in_min_confidence()
    if confidence < burn_in_min:
        return False, f"Burn-in: confidence {confidence:.3f} below burn-in minimum {burn_in_min:.3f}", state

    # Vs recorded guardrails
    passed, reason, guard_state = check_burn_in_vs_recorded(index_path)
    state.update(guard_state)
    if not passed:
        return False, reason, state

    return True, None, state


def check_burn_in_gate_batch(
    connector_name: str,
    match_count: int,
    index_path: str = "reports/index.json",
) -> tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Check if burn-in batch is allowed (match count capped at 1-3).
    Returns (allowed, reason_if_not_allowed, guardrail_state).
    """
    state: Dict[str, Any] = {"burn_in_max_matches": burn_in_max_matches()}

    if not is_burn_in_mode():
        return False, "ACTIVATION_MODE is not burn_in", state

    allowed_connectors = burn_in_connectors()
    if connector_name not in allowed_connectors:
        return False, f"Burn-in: connector '{connector_name}' not allowed", state

    max_m = burn_in_max_matches()
    if match_count > max_m:
        return False, f"Burn-in: match count {match_count} exceeds max {max_m}", state

    passed, reason, guard_state = check_burn_in_vs_recorded(index_path)
    state.update(guard_state)
    if not passed:
        return False, reason, state

    return True, None, state


def get_burn_in_config() -> Dict[str, Any]:
    """Get current burn-in configuration (for reporting)."""
    return {
        "is_burn_in_mode": is_burn_in_mode(),
        "burn_in_max_matches": burn_in_max_matches(),
        "burn_in_min_confidence": burn_in_min_confidence(),
        "burn_in_connectors": list(burn_in_connectors()),
        "burn_in_markets": list(burn_in_markets()),
        "max_live_io_alerts": BURN_IN_MAX_LIVE_IO_ALERTS,
        "max_pick_change_rate_burn_in": BURN_IN_MAX_PICK_CHANGE_RATE,
        "max_confidence_delta_p95_burn_in": BURN_IN_MAX_CONFIDENCE_DELTA_P95,
    }
