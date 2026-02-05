"""
Unit tests for controlled activation gate (require_activation_approval).
Guarantee activation cannot happen accidentally: default denied, token/pin/prereqs required.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from activation.activation_gate import (
    ActivationNotApprovedError,
    require_activation_approval,
    run_activation_with_approval_gate,
)
from policy.policy_runtime import get_active_policy


def test_default_activation_denied_when_activation_allowed_missing(caplog: pytest.LogCaptureFixture) -> None:
    """Default: activation denied when ACTIVATION_ALLOWED is missing or false."""
    import logging
    from ops.ops_events import OPS_LOGGER_NAME
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_ALLOWED", raising=False)
        m.delenv("ACTIVATION_APPROVAL_TOKEN", raising=False)
        context = {"approval_token": "any", "policy_version_pin": "v0"}
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "ACTIVATION_ALLOWED" in exc_info.value.detail
        assert "activation_not_approved" in caplog.text or "guardrail" in caplog.text.lower()


def test_activation_denied_when_activation_allowed_false(caplog: pytest.LogCaptureFixture) -> None:
    """Denied when ACTIVATION_ALLOWED is set to false."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "false")
        m.delenv("ACTIVATION_APPROVAL_TOKEN", raising=False)
        context = {"approval_token": "x", "policy_version_pin": "v0"}
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "ACTIVATION_ALLOWED" in exc_info.value.detail


def test_denied_if_token_missing(caplog: pytest.LogCaptureFixture) -> None:
    """Denied if ACTIVATION_APPROVAL_TOKEN is not set."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.delenv("ACTIVATION_APPROVAL_TOKEN", raising=False)
        context = {"approval_token": "secret", "policy_version_pin": "v0"}
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "APPROVAL_TOKEN" in exc_info.value.detail or "token" in exc_info.value.detail.lower()


def test_denied_if_token_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    """Denied if approval_token in context does not match ACTIVATION_APPROVAL_TOKEN."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.setenv("ACTIVATION_APPROVAL_TOKEN", "correct-token")
        context = {"approval_token": "wrong-token", "policy_version_pin": "v0"}
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "match" in exc_info.value.detail.lower() or "token" in exc_info.value.detail.lower()


def test_denied_if_policy_pin_missing(caplog: pytest.LogCaptureFixture) -> None:
    """Denied if policy_version_pin is missing from context."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.setenv("ACTIVATION_APPROVAL_TOKEN", "t")
        context = {"approval_token": "t"}
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "policy_version_pin" in exc_info.value.detail.lower()


def test_denied_if_policy_pin_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    """Denied if policy_version_pin does not equal current policy version."""
    current_version = get_active_policy().meta.version
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.setenv("ACTIVATION_APPROVAL_TOKEN", "t")
        m.setenv("MIN_OFFLINE_EVAL_RUNS", "0")
        context = {
            "approval_token": "t",
            "policy_version_pin": "wrong-version-xyz",
            "audit_trail_enabled": True,
            "index_path": None,
        }
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "policy_version_pin" in exc_info.value.detail or "version" in exc_info.value.detail


def test_denied_if_prerequisites_not_met_offline_eval(caplog: pytest.LogCaptureFixture) -> None:
    """Denied if offline_eval_runs < MIN_OFFLINE_EVAL_RUNS."""
    fake_index = {"runs": [], "quality_audit_runs": [], "activation_runs": [{"run_id": "a"}]}
    current_version = get_active_policy().meta.version
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.setenv("ACTIVATION_APPROVAL_TOKEN", "t")
        m.setenv("MIN_OFFLINE_EVAL_RUNS", "1000")
        m.setattr("reports.index_store.load_index", lambda path: fake_index)
        context = {
            "approval_token": "t",
            "policy_version_pin": current_version,
            "audit_trail_enabled": True,
            "index_path": "reports/index.json",
        }
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "offline_eval" in exc_info.value.detail or "MIN_OFFLINE" in exc_info.value.detail


def test_denied_if_audit_trail_not_met(caplog: pytest.LogCaptureFixture) -> None:
    """Denied if audit trail not enabled and no activation_runs in index."""
    fake_index = {"runs": [{"run_id": "r1"}], "quality_audit_runs": [], "activation_runs": []}
    current_version = get_active_policy().meta.version
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.setenv("ACTIVATION_APPROVAL_TOKEN", "t")
        m.setenv("MIN_OFFLINE_EVAL_RUNS", "0")
        m.setattr("reports.index_store.load_index", lambda path: fake_index)
        context = {
            "approval_token": "t",
            "policy_version_pin": current_version,
            "index_path": "reports/index.json",
        }
        with pytest.raises(ActivationNotApprovedError) as exc_info:
            require_activation_approval(context)
        assert exc_info.value.code == "ACTIVATION_NOT_APPROVED"
        assert "audit" in exc_info.value.detail.lower()


def test_allowed_when_all_conditions_satisfied(caplog: pytest.LogCaptureFixture) -> None:
    """Allowed only when ALL conditions are satisfied (fake context + env)."""
    fake_index = {
        "runs": [{"run_id": "r1"}],
        "quality_audit_runs": [{"run_id": "q1"}],
        "activation_runs": [{"run_id": "a1"}],
    }
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.setenv("ACTIVATION_APPROVAL_TOKEN", "secret123")
        m.setenv("MIN_OFFLINE_EVAL_RUNS", "0")
        m.setattr("reports.index_store.load_index", lambda path: fake_index)
        m.setattr("activation.activation_gate._policy_history_exists", lambda: True)
        current_version = get_active_policy().meta.version
        context = {
            "approval_token": "secret123",
            "policy_version_pin": current_version,
            "audit_trail_enabled": True,
            "index_path": "reports/index.json",
        }
        require_activation_approval(context)
    # No exception; if we get here, allowed.


def test_guardrail_trigger_emitted_on_denial(caplog: pytest.LogCaptureFixture) -> None:
    """Guardrail trigger log is emitted on denial (ops_events)."""
    import logging
    from ops.ops_events import OPS_LOGGER_NAME
    caplog.set_level(logging.INFO, logger=OPS_LOGGER_NAME)
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_ALLOWED", raising=False)
        context = {"approval_token": "x", "policy_version_pin": "v0"}
        with pytest.raises(ActivationNotApprovedError):
            require_activation_approval(context)
    assert "activation_not_approved" in caplog.text or "guardrail_trigger" in caplog.text


def test_run_activation_with_approval_gate_calls_require_and_passes() -> None:
    """Stub runner run_activation_with_approval_gate calls gate; passes when all satisfied."""
    fake_index = {
        "runs": [{"run_id": "r1"}],
        "quality_audit_runs": [],
        "activation_runs": [{"run_id": "a1"}],
    }
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ACTIVATION_ALLOWED", "true")
        m.setenv("ACTIVATION_APPROVAL_TOKEN", "t")
        m.setenv("MIN_OFFLINE_EVAL_RUNS", "0")
        m.setattr("reports.index_store.load_index", lambda path: fake_index)
        m.setattr("activation.activation_gate._policy_history_exists", lambda: True)
        current_version = get_active_policy().meta.version
        context = {
            "approval_token": "t",
            "policy_version_pin": current_version,
            "audit_trail_enabled": True,
            "index_path": "reports/index.json",
        }
        run_activation_with_approval_gate(context)
    # No exception


def test_run_activation_with_approval_gate_raises_on_denial() -> None:
    """Stub runner raises when gate denies."""
    with pytest.MonkeyPatch.context() as m:
        m.delenv("ACTIVATION_ALLOWED", raising=False)
        context = {"approval_token": "x", "policy_version_pin": "v0"}
        with pytest.raises(ActivationNotApprovedError):
            run_activation_with_approval_gate(context)
