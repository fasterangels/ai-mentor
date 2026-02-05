"""
Activation Gate: controlled, opt-in, reversible activation of decisions.
Requires multiple conditions and enforces limited scope.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from reports.index_store import load_index


def _kill_switch_active() -> bool:
    """Hard kill-switch that forces shadow-only regardless of other flags."""
    return os.environ.get("ACTIVATION_KILL_SWITCH", "").strip().lower() in ("1", "true", "yes")


def _activation_enabled() -> bool:
    """Check if activation is enabled via env."""
    return os.environ.get("ACTIVATION_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _activation_mode() -> str:
    """Get activation mode: 'limited', 'burn_in', or 'expanded' for activation."""
    return os.environ.get("ACTIVATION_MODE", "").strip().lower()


def _activation_tier() -> str:
    """ACTIVATION_TIER: burn_in, limited, expanded. Default burn_in."""
    from activation.tiers import _tier
    return _tier()


def _live_writes_allowed() -> bool:
    """Check if live writes are allowed."""
    return os.environ.get("LIVE_WRITES_ALLOWED", "").strip().lower() in ("1", "true", "yes")


def _activation_connectors() -> Set[str]:
    """Get whitelist of connectors allowed for activation."""
    connectors_str = os.environ.get("ACTIVATION_CONNECTORS", "").strip()
    if not connectors_str:
        return set()
    return {c.strip() for c in connectors_str.split(",") if c.strip()}


def _activation_markets() -> Set[str]:
    """Get whitelist of markets allowed for activation (default: 1X2 only)."""
    markets_str = os.environ.get("ACTIVATION_MARKETS", "").strip()
    if markets_str:
        return {m.strip() for m in markets_str.split(",") if m.strip()}
    return {"1X2"}  # Default: 1X2 only


def _activation_max_matches() -> int:
    """Get max matches per run; capped by tier and ACTIVATION_MAX_MATCHES_HARD_CAP."""
    from activation.tiers import tier_max_matches
    # Use activation mode as effective tier for caps (limited/expanded get env cap, burn_in gets 1-3)
    return tier_max_matches(_activation_mode())


def _activation_min_confidence() -> float:
    """Get tier-specific minimum confidence for activation (stricter than policy when set)."""
    from activation.tiers import tier_min_confidence
    return tier_min_confidence(_activation_mode())


def _check_readiness() -> tuple[bool, Optional[str]]:
    """
    Check system readiness for activation.
    Returns (ready, reason_if_not_ready).
    """
    # Basic readiness checks (can be extended)
    # For now, just check that we're not in a degraded state
    # In production, this could check DB connectivity, cache health, etc.
    return True, None


def _check_live_shadow_guardrails(
    index_path: str = "reports/index.json",
    max_runs: int = 5,
    require_no_critical_alerts: bool = True,
) -> tuple[bool, Optional[str]]:
    """
    Check that recent live shadow runs have no critical alerts.
    Returns (pass, reason_if_fail).
    """
    try:
        index = load_index(index_path)
        # Check live shadow analyze runs (most recent)
        runs = index.get("live_shadow_analyze_runs") or []
        if not runs:
            return True, None  # No runs yet, allow activation
        
        recent_runs = runs[-max_runs:]
        for run in recent_runs:
            alerts_count = run.get("alerts_count", 0)
            if require_no_critical_alerts and alerts_count > 0:
                # Check if any alerts are critical
                # For now, any alert is considered critical
                return False, f"Recent live shadow run {run.get('run_id')} has {alerts_count} alert(s)"
        return True, None
    except Exception:  # noqa: BLE001
        # If we can't check guardrails, be conservative
        return False, "Unable to check live shadow guardrails"


def check_activation_gate(
    connector_name: str,
    market: str,
    confidence: float,
    policy_min_confidence: float,
    index_path: str = "reports/index.json",
) -> tuple[bool, Optional[str]]:
    """
    Check if activation is allowed for a specific decision.
    Returns (allowed, reason_if_not_allowed).
    
    Args:
        connector_name: Connector name
        market: Market name (e.g., "1X2")
        confidence: Decision confidence
        policy_min_confidence: Policy minimum confidence threshold
        index_path: Path to reports index for guardrail checks
    """
    # 1. Kill-switch check (highest priority)
    if _kill_switch_active():
        return False, "ACTIVATION_KILL_SWITCH is enabled"
    
    # 2. Basic env checks
    if not _activation_enabled():
        return False, "ACTIVATION_ENABLED is not set"
    
    mode = _activation_mode()
    if mode not in ("limited", "burn_in", "expanded"):
        return False, f"ACTIVATION_MODE must be 'limited', 'burn_in', or 'expanded' (got '{mode}')"
    
    if not _live_writes_allowed():
        return False, "LIVE_WRITES_ALLOWED is not set"
    
    # Burn-in: also requires LIVE_IO_ALLOWED
    if mode == "burn_in":
        from ingestion.live_io import live_io_allowed
        if not live_io_allowed():
            return False, "LIVE_IO_ALLOWED is not set (required for burn-in)"
    
    # Burn-in: use stricter burn-in gate
    if mode == "burn_in":
        from activation.burn_in import check_burn_in_gate
        allowed, reason, guardrail_state = check_burn_in_gate(
            connector_name=connector_name,
            market=market,
            confidence=confidence,
            policy_min_confidence=policy_min_confidence,
            index_path=index_path,
        )
        return allowed, reason
    
    # 3. Readiness checks (limited mode)
    ready, reason = _check_readiness()
    if not ready:
        return False, f"Readiness check failed: {reason}"
    
    # 4. Connector whitelist
    allowed_connectors = _activation_connectors()
    if allowed_connectors and connector_name not in allowed_connectors:
        return False, f"Connector '{connector_name}' not in ACTIVATION_CONNECTORS whitelist"
    
    # 5. Market whitelist
    allowed_markets = _activation_markets()
    if market not in allowed_markets:
        return False, f"Market '{market}' not in ACTIVATION_MARKETS whitelist"
    
    # 6. Confidence thresholds
    if confidence < policy_min_confidence:
        return False, f"Confidence {confidence:.3f} below policy minimum {policy_min_confidence:.3f}"
    
    activation_min_conf = _activation_min_confidence()
    if activation_min_conf > 0.0 and confidence < activation_min_conf:
        return False, f"Confidence {confidence:.3f} below activation minimum {activation_min_conf:.3f}"
    
    # 7. Live shadow guardrails
    guardrails_pass, reason = _check_live_shadow_guardrails(index_path)
    if not guardrails_pass:
        return False, f"Live shadow guardrails check failed: {reason}"
    
    return True, None


def check_activation_gate_batch(
    connector_name: str,
    match_count: int,
    index_path: str = "reports/index.json",
) -> tuple[bool, Optional[str]]:
    """
    Check if activation is allowed for a batch run.
    Returns (allowed, reason_if_not_allowed).
    
    Args:
        connector_name: Connector name
        match_count: Number of matches in batch
        index_path: Path to reports index
    """
    # 1. Kill-switch check
    if _kill_switch_active():
        return False, "ACTIVATION_KILL_SWITCH is enabled"
    
    # 2. Basic env checks
    if not _activation_enabled():
        return False, "ACTIVATION_ENABLED is not set"
    
    mode = _activation_mode()
    if mode not in ("limited", "burn_in", "expanded"):
        return False, f"ACTIVATION_MODE must be 'limited', 'burn_in', or 'expanded' (got '{mode}')"
    
    if not _live_writes_allowed():
        return False, "LIVE_WRITES_ALLOWED is not set"
    
    # Burn-in: also requires LIVE_IO_ALLOWED
    if mode == "burn_in":
        from ingestion.live_io import live_io_allowed
        if not live_io_allowed():
            return False, "LIVE_IO_ALLOWED is not set (required for burn-in)"
    
    # Burn-in: use burn-in batch gate (caps 1-3, real_provider only)
    if mode == "burn_in":
        from activation.burn_in import check_burn_in_gate_batch
        allowed, reason, _ = check_burn_in_gate_batch(
            connector_name=connector_name,
            match_count=match_count,
            index_path=index_path,
        )
        return allowed, reason
    
    # 3. Connector whitelist
    allowed_connectors = _activation_connectors()
    if allowed_connectors and connector_name not in allowed_connectors:
        return False, f"Connector '{connector_name}' not in ACTIVATION_CONNECTORS whitelist"
    
    # 4. Max matches limit (tier-capped, hard cap 10)
    max_matches = _activation_max_matches()
    if max_matches <= 0:
        return False, "ACTIVATION_MAX_MATCHES not set or 0 (required for limited/expanded)"
    if match_count > max_matches:
        return False, f"Match count {match_count} exceeds tier cap ACTIVATION_MAX_MATCHES={max_matches}"
    
    # 5. Readiness checks
    ready, reason = _check_readiness()
    if not ready:
        return False, f"Readiness check failed: {reason}"
    
    # 6. Live shadow guardrails
    guardrails_pass, reason = _check_live_shadow_guardrails(index_path)
    if not guardrails_pass:
        return False, f"Live shadow guardrails check failed: {reason}"
    
    return True, None


def get_activation_config() -> Dict[str, Any]:
    """Get current activation configuration (for reporting)."""
    config = {
        "kill_switch_active": _kill_switch_active(),
        "activation_enabled": _activation_enabled(),
        "activation_mode": _activation_mode(),
        "activation_tier": _activation_tier(),
        "live_writes_allowed": _live_writes_allowed(),
        "allowed_connectors": list(_activation_connectors()),
        "allowed_markets": list(_activation_markets()),
        "max_matches": _activation_max_matches(),
        "activation_min_confidence": _activation_min_confidence(),
    }
    try:
        from activation.tiers import get_tier_config, _rollout_pct, _daily_max_activations
        config["tier_config"] = get_tier_config()
        config["rollout_pct"] = _rollout_pct()
        config["daily_max_activations"] = _daily_max_activations()
    except Exception:  # noqa: BLE001
        pass
    if _activation_mode() == "burn_in":
        from activation.burn_in import get_burn_in_config
        config["burn_in"] = get_burn_in_config()
    return config