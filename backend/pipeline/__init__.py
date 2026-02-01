"""Data Pipeline: Multi-source collection, quality gates, consensus, and caching.

This module orchestrates data collection from multiple sources, enforces quality
gates, builds consensus, caches results, and produces Evidence Packs for downstream
analysis. No analyzer logic - prepares trusted inputs only.
"""

from .pipeline import run_pipeline
from .types import (
    DomainData,
    EvidencePack,
    PipelineInput,
    PipelineResult,
    QualityReport,
)

__all__ = [
    "run_pipeline",
    "PipelineInput",
    "PipelineResult",
    "EvidencePack",
    "DomainData",
    "QualityReport",
]
