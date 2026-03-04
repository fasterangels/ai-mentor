"""Refusal threshold optimization (shadow-only): grid search over thresholds using uncertainty-shadow + outcomes."""

from .grid_search import full_grid_results, grid_search_best_thresholds, would_refuse
from .model import (
    ALPHA,
    BestThresholds,
    ShadowDecision,
    STALE_BANDS,
    effective_confidence_grid,
)

__all__ = [
    "ALPHA",
    "BestThresholds",
    "ShadowDecision",
    "STALE_BANDS",
    "effective_confidence_grid",
    "full_grid_results",
    "grid_search_best_thresholds",
    "would_refuse",
]
