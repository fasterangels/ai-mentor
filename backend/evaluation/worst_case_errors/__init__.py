"""Worst-case error tracking (measurement-only): score and rank evaluated decisions by loss severity."""

from .compute import compute_worst_case_report
from .model import (
    EvaluatedDecision,
    UncertaintyShadow,
    WorstCaseReport,
    WorstCaseRow,
)
from .score import worst_case_score

__all__ = [
    "EvaluatedDecision",
    "UncertaintyShadow",
    "WorstCaseReport",
    "WorstCaseRow",
    "compute_worst_case_report",
    "worst_case_score",
]
