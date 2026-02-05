"""Activation module: controlled, opt-in, reversible activation of decisions."""

from activation.activation_gate import (
    ActivationNotApprovedError,
    require_activation_approval,
    run_activation_with_approval_gate,
)

__all__ = [
    "ActivationNotApprovedError",
    "require_activation_approval",
    "run_activation_with_approval_gate",
]
