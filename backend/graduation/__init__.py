"""Graduation criteria: formal pass/fail gates (measurement-only)."""

from .criteria_v1 import CriterionResult, GraduationResult
from .evaluate import evaluate_graduation

__all__ = ["CriterionResult", "GraduationResult", "evaluate_graduation"]
