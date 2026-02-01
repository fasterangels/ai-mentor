"""Evaluation & Performance Loop: compare predictions with results, record outcomes, KPIs."""

from .evaluator import evaluate_prediction
from .evaluation_v2 import (
    compute_metrics,
    compute_output_hash,
    run_stability_check,
)
from .metrics import get_kpis
from .types import EvaluationResult, KPIReport, MarketOutcome

__all__ = [
    "evaluate_prediction",
    "get_kpis",
    "EvaluationResult",
    "KPIReport",
    "MarketOutcome",
    "compute_metrics",
    "compute_output_hash",
    "run_stability_check",
]
