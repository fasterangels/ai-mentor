"""
Controlled activation: manual approval gate.
Activation is OFF by default. Requires explicit ACTIVATION_ALLOWED=true,
ACTIVATION_APPROVAL_TOKEN match, POLICY_VERSION_PIN match, and prerequisites.
Raises ACTIVATION_NOT_APPROVED on any failure; logs guardrail trigger.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

# Default minimum offline eval runs (env MIN_OFFLINE_EVAL_RUNS)
DEFAULT_MIN_OFFLINE_EVAL_RUNS = 365


class ActivationNotApprovedError(Exception):
    """Raised when require_activation_approval() fails. code is always ACTIVATION_NOT_APPROVED."""

    def __init__(self, code: str, detail: str) -> None:
        assert code == "ACTIVATION_NOT_APPROVED"
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _activation_allowed_env() -> bool:
    """ACTIVATION_ALLOWED must be exactly 'true' (case-sensitive for strictness, or accept true)."""
    return os.environ.get("ACTIVATION_ALLOWED", "").strip().lower() == "true"


def _required_approval_token() -> Optional[str]:
    """Token that must be provided in context (from env ACTIVATION_APPROVAL_TOKEN)."""
    s = os.environ.get("ACTIVATION_APPROVAL_TOKEN", "").strip()
    return s if s else None


def _min_offline_eval_runs() -> int:
    try:
        return max(0, int(os.environ.get("MIN_OFFLINE_EVAL_RUNS", str(DEFAULT_MIN_OFFLINE_EVAL_RUNS))))
    except ValueError:
        return DEFAULT_MIN_OFFLINE_EVAL_RUNS


def _count_offline_eval_runs(index_path: str | Path) -> int:
    """Count runs that represent offline eval history (index 'runs' + quality_audit_runs)."""
    from reports.index_store import load_index
    index = load_index(index_path)
    runs = index.get("runs") or []
    quality_runs = index.get("quality_audit_runs") or []
    return len(runs) + len(quality_runs)


def _audit_trail_enabled_or_exists(context: Dict[str, Any], index_path: str | Path) -> bool:
    """Audit trail: either context says audit enabled, or index has activation_runs (audit record)."""
    if context.get("audit_trail_enabled") is True:
        return True
    from reports.index_store import load_index
    index = load_index(index_path)
    activation_runs = index.get("activation_runs") or []
    return len(activation_runs) > 0


def _policy_history_exists() -> bool:
    """Policy history: policy repo dir or POLICY_PATH file exists."""
    from policy.policy_store import default_policy_path
    path_str = os.environ.get("POLICY_PATH")
    if path_str:
        p = Path(path_str)
        return p.is_file() or (p.parent.is_dir() and p.parent != Path.cwd().root)
    default_path = default_policy_path()
    return default_path.is_file() or default_path.parent.is_dir()


def _current_policy_version() -> str:
    """Current policy version string from active policy."""
    from policy.policy_runtime import get_active_policy
    policy = get_active_policy()
    return (policy.meta.version if policy and policy.meta else "v0")


def require_activation_approval(context: Dict[str, Any]) -> None:
    """
    Enforce manual activation gate. Raises ActivationNotApprovedError with code
    ACTIVATION_NOT_APPROVED if any check fails. Logs guardrail trigger on denial.
    Context must include: approval_token (str), policy_version_pin (str).
    Optional: index_path (str|Path), audit_trail_enabled (bool).
    """
    from ops.ops_events import log_guardrail_trigger

    index_path = context.get("index_path") or "reports/index.json"

    # A) ACTIVATION_ALLOWED env must be exactly "true"
    if not _activation_allowed_env():
        detail = "ACTIVATION_ALLOWED is not exactly true (default off)"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=None)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)

    # B) ACTIVATION_APPROVAL_TOKEN must be present and match context
    required_token = _required_approval_token()
    if not required_token:
        detail = "ACTIVATION_APPROVAL_TOKEN is not set"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=None)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)
    provided_token = context.get("approval_token")
    if provided_token is None or provided_token != required_token:
        detail = "approval_token missing or does not match ACTIVATION_APPROVAL_TOKEN"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=None)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)

    # C) POLICY_VERSION_PIN must equal policy version used for the run
    pin = context.get("policy_version_pin")
    if pin is None or not str(pin).strip():
        detail = "policy_version_pin is missing"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=None)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)
    current = _current_policy_version()
    if str(pin).strip() != current:
        detail = f"policy_version_pin {pin!r} does not match current policy version {current!r}"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=None)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)

    # D) Prerequisites
    min_runs = _min_offline_eval_runs()
    count = _count_offline_eval_runs(index_path)
    if count < min_runs:
        detail = f"offline_eval_runs {count} < MIN_OFFLINE_EVAL_RUNS {min_runs}"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=min_runs)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)

    if not _audit_trail_enabled_or_exists(context, index_path):
        detail = "audit trail not enabled and no activation_runs in index"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=None)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)

    if not _policy_history_exists():
        detail = "policy history (policy repo dir or POLICY_PATH) does not exist"
        log_guardrail_trigger("activation_not_approved", detail, cap_value=None)
        raise ActivationNotApprovedError("ACTIVATION_NOT_APPROVED", detail)


def run_activation_with_approval_gate(context: Dict[str, Any]) -> None:
    """
    Stub activation runner: call this before any production activation.
    Enforces require_activation_approval(context). If it returns, approval passed.
    Not called by shadow pipeline or default flows. Backend-only.
    """
    require_activation_approval(context)
