"""
Unit tests for activation gate: env checks, whitelists, confidence thresholds, guardrails.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from activation.gate import (
    _activation_connectors,
    _activation_enabled,
    _activation_markets,
    _activation_max_matches,
    _activation_min_confidence,
    _kill_switch_active,
    check_activation_gate,
    check_activation_gate_batch,
    get_activation_config,
)


def test_kill_switch_overrides_everything() -> None:
    """Kill-switch forces shadow-only regardless of other flags."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_KILL_SWITCH", "true")
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider")
        
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "KILL_SWITCH" in reason.upper()


def test_activation_requires_all_env_flags() -> None:
    """Activation requires ACTIVATION_ENABLED, ACTIVATION_MODE=limited, LIVE_WRITES_ALLOWED."""
    # Missing ACTIVATION_ENABLED
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_ENABLED", raising=False)
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "ACTIVATION_ENABLED" in reason
    
    # Wrong ACTIVATION_MODE
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "full")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "limited" in reason.lower()
    
    # Missing LIVE_WRITES_ALLOWED
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.delenv("LIVE_WRITES_ALLOWED", raising=False)
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "LIVE_WRITES_ALLOWED" in reason


def test_connector_whitelist_enforcement() -> None:
    """Connector must be in ACTIVATION_CONNECTORS whitelist if set."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider,stub_live_platform")
        
        # Allowed connector
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        # May fail on guardrails, but not on connector whitelist
        if not allowed:
            assert "connector" not in reason.lower() or "whitelist" not in reason.lower()
        
        # Disallowed connector
        allowed, reason = check_activation_gate(
            connector_name="sample_platform",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "connector" in reason.lower() or "whitelist" in reason.lower()


def test_market_whitelist_enforcement() -> None:
    """Market must be in ACTIVATION_MARKETS whitelist (default: 1X2 only)."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider")
        
        # Default: 1X2 allowed
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        # May fail on guardrails, but not on market whitelist
        if not allowed:
            assert "market" not in reason.lower() or "whitelist" not in reason.lower()
        
        # OU_2.5 not in default whitelist
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="OU_2.5",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "market" in reason.lower() or "whitelist" in reason.lower()
        
        # Custom whitelist
        m.setenv("ACTIVATION_MARKETS", "1X2,OU_2.5")
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="OU_2.5",
            confidence=0.9,
            policy_min_confidence=0.7,
        )
        # May fail on guardrails, but not on market whitelist
        if not allowed:
            assert "market" not in reason.lower() or "whitelist" not in reason.lower()


def test_confidence_thresholds() -> None:
    """Confidence must meet policy minimum and activation minimum."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider")
        
        # Below policy minimum
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.5,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "confidence" in reason.lower() or "policy" in reason.lower()
        
        # Below activation minimum
        m.setenv("ACTIVATION_MIN_CONFIDENCE", "0.85")
        allowed, reason = check_activation_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.8,
            policy_min_confidence=0.7,
        )
        assert not allowed
        assert "activation" in reason.lower() or "confidence" in reason.lower()


def test_max_matches_limit() -> None:
    """Batch activation respects ACTIVATION_MAX_MATCHES limit."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider")
        m.setenv("ACTIVATION_MAX_MATCHES", "5")
        
        # Within limit
        allowed, reason = check_activation_gate_batch(
            connector_name="real_provider",
            match_count=3,
        )
        # May fail on guardrails, but not on max matches
        if not allowed:
            assert "match" not in reason.lower() or "max" not in reason.lower()
        
        # Exceeds limit
        allowed, reason = check_activation_gate_batch(
            connector_name="real_provider",
            match_count=10,
        )
        assert not allowed
        assert "match" in reason.lower() or "max" in reason.lower()


def test_get_activation_config() -> None:
    """get_activation_config returns current configuration."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ENABLED", "true")
        m.setenv("ACTIVATION_MODE", "limited")
        m.setenv("LIVE_WRITES_ALLOWED", "true")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider,stub")
        m.setenv("ACTIVATION_MARKETS", "1X2,OU_2.5")
        m.setenv("ACTIVATION_MAX_MATCHES", "10")
        m.setenv("ACTIVATION_MIN_CONFIDENCE", "0.8")
        
        config = get_activation_config()
        assert config["activation_enabled"] is True
        assert config["activation_mode"] == "limited"
        assert config["live_writes_allowed"] is True
        assert "real_provider" in config["allowed_connectors"]
        assert "1X2" in config["allowed_markets"]
        assert config["max_matches"] == 10
        assert config["activation_min_confidence"] == 0.8
