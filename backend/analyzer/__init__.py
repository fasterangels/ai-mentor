"""Analyzer Engine v1: Deterministic decision engine for market predictions.

This module provides a deterministic analyzer that consumes Evidence Packs
and produces market-level decisions with probabilities, separation, confidence,
risk, and reasons. No ML, no learning - pure reproducible logic.
"""

from .engine_v1 import analyze
from .policies import AnalyzerPolicy, default_policy
from .types import AnalyzerInput, AnalyzerResult, MarketDecision

__all__ = [
    "analyze",
    "AnalyzerInput",
    "AnalyzerResult",
    "MarketDecision",
    "AnalyzerPolicy",
    "default_policy",
]
