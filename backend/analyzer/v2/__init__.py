"""Analyzer v2 — Quality gates, decision contract, conflict handling.

See docs/analyzer_v2_spec.md for full specification.
"""

from .contracts import (
    ANALYZER_VERSION_DEFAULT,
    ANALYZER_VERSION_V1,
    ANALYZER_VERSION_V2,
    CONFLICT_T1_BLOCK,
    CONFLICT_T2_DOWNGRADE,
    MAX_DECISION_REASONS,
    MAX_MINOR_FLAGS_BEFORE_NO_BET,
    OVERRIDE_CONFIDENCE_WHEN_BELOW_T2,
    POLICY_VERSION_V2,
    SUPPORTED_MARKETS_V2,
    THRESHOLD_EVIDENCE_QUALITY,
    DecisionKind,
    GateId,
    MarketFlag,
    Selection1X2,
    SelectionBTTS,
    SelectionOU25,
)

__all__ = [
    "ANALYZER_VERSION_DEFAULT",
    "ANALYZER_VERSION_V1",
    "ANALYZER_VERSION_V2",
    "CONFLICT_T1_BLOCK",
    "CONFLICT_T2_DOWNGRADE",
    "MAX_DECISION_REASONS",
    "MAX_MINOR_FLAGS_BEFORE_NO_BET",
    "OVERRIDE_CONFIDENCE_WHEN_BELOW_T2",
    "POLICY_VERSION_V2",
    "SUPPORTED_MARKETS_V2",
    "THRESHOLD_EVIDENCE_QUALITY",
    "DecisionKind",
    "GateId",
    "MarketFlag",
    "Selection1X2",
    "SelectionBTTS",
    "SelectionOU25",
]
