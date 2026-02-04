"""
Unit tests for burn-in mode: caps 1-3, stricter thresholds, connector/market whitelist, guardrails.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from activation.burn_in import (
    BURN_IN_MAX_MATCHES_DEFAULT,
    BURN_IN_MAX_MATCHES_MAX,
    BURN_IN_MAX_MATCHES_MIN,
    burn_in_connectors,
    burn_in_markets,
    burn_in_max_matches,
    burn_in_min_confidence,
    check_burn_in_gate,
    check_burn_in_gate_batch,
    check_burn_in_live_io_alerts,
    get_burn_in_config,
    is_burn_in_mode,
)


def test_burn_in_max_matches_default_and_cap() -> None:
    """ACTIVATION_MAX_MATCHES for burn-in is capped 1-3; default 1."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_MAX_MATCHES", raising=False)
        assert burn_in_max_matches() == BURN_IN_MAX_MATCHES_DEFAULT
        assert burn_in_max_matches() == 1
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MAX_MATCHES", "2")
        assert burn_in_max_matches() == 2
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MAX_MATCHES", "3")
        assert burn_in_max_matches() == 3
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MAX_MATCHES", "10")
        assert burn_in_max_matches() == BURN_IN_MAX_MATCHES_MAX
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MAX_MATCHES", "0")
        assert burn_in_max_matches() == BURN_IN_MAX_MATCHES_MIN


def test_burn_in_min_confidence_stricter_than_policy() -> None:
    """Burn-in min confidence is a separate higher threshold (default 0.85)."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_MIN_CONFIDENCE_BURN_IN", raising=False)
        assert burn_in_min_confidence() >= 0.85
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MIN_CONFIDENCE_BURN_IN", "0.9")
        assert burn_in_min_confidence() == 0.9


def test_burn_in_connectors_default_real_provider() -> None:
    """Burn-in connector whitelist defaults to real_provider only."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_CONNECTORS", raising=False)
        conns = burn_in_connectors()
        assert "real_provider" in conns
        assert len(conns) >= 1
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_CONNECTORS", "real_provider,stub_live_platform")
        conns = burn_in_connectors()
        assert "real_provider" in conns
        assert "stub_live_platform" in conns


def test_burn_in_markets_default_1x2() -> None:
    """Burn-in market whitelist defaults to 1X2 only."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_MARKETS", raising=False)
        markets = burn_in_markets()
        assert "1X2" in markets
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MARKETS", "1X2,OU_2.5")
        markets = burn_in_markets()
        assert "1X2" in markets
        assert "OU_2.5" in markets


def test_check_burn_in_live_io_alerts_zero_tolerance() -> None:
    """Any critical live IO alert fails burn-in (max_live_io_alerts=0)."""
    ok, reason = check_burn_in_live_io_alerts([], max_alerts=0)
    assert ok is True
    assert reason is None
    ok, reason = check_burn_in_live_io_alerts([{"id": "a"}], max_alerts=0)
    assert ok is False
    assert "exceeds max" in reason


def test_check_burn_in_gate_connector_market_confidence(tmp_path) -> None:
    """Burn-in gate enforces connector, market whitelist and burn-in min confidence."""
    index_path = str(tmp_path / "index.json")
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "index.json").write_text("{}", encoding="utf-8")

    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MODE", "burn_in")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider")
        m.setenv("ACTIVATION_MARKETS", "1X2")
        m.setenv("ACTIVATION_MIN_CONFIDENCE_BURN_IN", "0.88")

        # Allowed: real_provider, 1X2, confidence above 0.88 and policy 0.7
        allowed, reason, state = check_burn_in_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
            index_path=index_path,
        )
        assert allowed is True
        assert reason is None
        assert state.get("burn_in_confidence_gate") == 0.88

        # Reject connector
        allowed, reason, _ = check_burn_in_gate(
            connector_name="other_connector",
            market="1X2",
            confidence=0.9,
            policy_min_confidence=0.7,
            index_path=index_path,
        )
        assert allowed is False
        assert "connector" in reason.lower()

        # Reject market
        allowed, reason, _ = check_burn_in_gate(
            connector_name="real_provider",
            market="OU_2.5",
            confidence=0.9,
            policy_min_confidence=0.7,
            index_path=index_path,
        )
        assert allowed is False
        assert "market" in reason.lower()

        # Reject confidence below burn-in min
        allowed, reason, _ = check_burn_in_gate(
            connector_name="real_provider",
            market="1X2",
            confidence=0.85,
            policy_min_confidence=0.7,
            index_path=index_path,
        )
        assert allowed is False
        assert "burn-in" in reason.lower() or "confidence" in reason.lower()


def test_check_burn_in_gate_batch_caps(tmp_path) -> None:
    """Burn-in batch gate enforces match count cap (1-3)."""
    index_path = str(tmp_path / "index.json")
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "index.json").write_text("{}", encoding="utf-8")

    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MODE", "burn_in")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider")
        m.setenv("ACTIVATION_MAX_MATCHES", "1")

        allowed, reason, state = check_burn_in_gate_batch(
            connector_name="real_provider",
            match_count=1,
            index_path=index_path,
        )
        assert allowed is True
        assert state.get("burn_in_max_matches") == 1

        allowed, reason, _ = check_burn_in_gate_batch(
            connector_name="real_provider",
            match_count=2,
            index_path=index_path,
        )
        assert allowed is False
        assert "match" in reason.lower() or "exceeds" in reason.lower()


def test_burn_in_thresholds_stricter_than_normal() -> None:
    """Burn-in min confidence is stricter than typical activation min (default 0.85 vs 0)."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_MIN_CONFIDENCE_BURN_IN", raising=False)
        burn_in_min = burn_in_min_confidence()
        assert burn_in_min >= 0.85
    from activation.gate import _activation_min_confidence
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_MIN_CONFIDENCE", raising=False)
        limited_min = _activation_min_confidence()
    assert burn_in_min >= limited_min


def test_get_burn_in_config() -> None:
    """get_burn_in_config returns is_burn_in_mode, caps, thresholds, guardrails."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_MODE", "burn_in")
        m.setenv("ACTIVATION_CONNECTORS", "real_provider")
        m.setenv("ACTIVATION_MAX_MATCHES", "1")
        config = get_burn_in_config()
        assert config["is_burn_in_mode"] is True
        assert config["burn_in_max_matches"] == 1
        assert "burn_in_min_confidence" in config
        assert "real_provider" in config["burn_in_connectors"]
        assert config["max_live_io_alerts"] == 0
