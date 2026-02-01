"""Analyzer v2 — Decision contract, flags, gates, and version constants.

BLOCK 10 — No full logic; enums/constants only. See docs/analyzer_v2_spec.md.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

# -----------------------------------------------------------------------------
# Version selector (request body: analyzer_version = "v1" | "v2")
# -----------------------------------------------------------------------------
ANALYZER_VERSION_V1 = "v1"
ANALYZER_VERSION_V2 = "v2"
ANALYZER_VERSION_DEFAULT = ANALYZER_VERSION_V1

# -----------------------------------------------------------------------------
# Decision contract — canonical decision kind
# -----------------------------------------------------------------------------


class DecisionKind(StrEnum):
    """Canonical decision outcome per market."""

    PLAY = "PLAY"
    NO_BET = "NO_BET"
    NO_PREDICTION = "NO_PREDICTION"


# -----------------------------------------------------------------------------
# Selection vocabularies (only when decision == PLAY)
# -----------------------------------------------------------------------------


class Selection1X2(StrEnum):
    """1X2 market selection."""

    HOME = "HOME"
    DRAW = "DRAW"
    AWAY = "AWAY"


class SelectionOU25(StrEnum):
    """OU_2.5 market selection."""

    OVER = "OVER"
    UNDER = "UNDER"


class SelectionBTTS(StrEnum):
    """BTTS market selection."""

    YES = "YES"
    NO = "NO"


# -----------------------------------------------------------------------------
# Markets supported in v2 (initial set)
# -----------------------------------------------------------------------------
MARKET_1X2 = "1X2"
MARKET_OU_25 = "OU_2.5"
MARKET_BTTS = "BTTS"

SUPPORTED_MARKETS_V2: tuple[str, ...] = (MARKET_1X2, MARKET_OU_25, MARKET_BTTS)

# -----------------------------------------------------------------------------
# Flags vocabulary (controlled)
# -----------------------------------------------------------------------------


class MarketFlag(StrEnum):
    """Controlled vocabulary for decision and run-level flags."""

    DATA_SPARSE = "DATA_SPARSE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SIGNAL_CONTRADICTION = "SIGNAL_CONTRADICTION"
    LOW_QUALITY_EVIDENCE = "LOW_QUALITY_EVIDENCE"
    OUTLIER_DETECTED = "OUTLIER_DETECTED"
    SMALL_SAMPLE = "SMALL_SAMPLE"
    STALE_DATA = "STALE_DATA"
    MISSING_KEY_FEATURES = "MISSING_KEY_FEATURES"
    CONSENSUS_WEAK = "CONSENSUS_WEAK"
    MARKET_NOT_SUPPORTED = "MARKET_NOT_SUPPORTED"
    INTERNAL_GUARDRAIL_TRIGGERED = "INTERNAL_GUARDRAIL_TRIGGERED"
    # Resolver-derived (mapped when resolver != RESOLVED)
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"


# All valid flag strings (for validation / iteration)
ALL_MARKET_FLAGS: frozenset[str] = frozenset(f.value for f in MarketFlag)

# -----------------------------------------------------------------------------
# Quality gate IDs (for gate_results)
# -----------------------------------------------------------------------------


class GateId(StrEnum):
    """Identifiers for quality gates in analysis_run.gate_results."""

    RESOLVER = "resolver"
    MISSING_KEY_FEATURES = "missing_key_features"
    EVIDENCE_QUALITY = "evidence_quality"
    SOURCE_CONFLICT = "source_conflict"
    SIGNAL_CONTRADICTION = "signal_contradiction"
    MARKET_SUPPORTED = "market_supported"
    SOFT_BORDERLINE_CONFIDENCE = "soft_borderline_confidence"
    SOFT_MINOR_FLAGS = "soft_minor_flags"


# -----------------------------------------------------------------------------
# Policy version and decision contract limits
# -----------------------------------------------------------------------------
POLICY_VERSION_V2 = "v2.0.0"
MAX_DECISION_REASONS = 10

# -----------------------------------------------------------------------------
# Conflict handling thresholds
# -----------------------------------------------------------------------------
# consensus_quality < T1 => NO_PREDICTION (block)
CONFLICT_T1_BLOCK = 0.4
# T1 <= consensus_quality < T2 => NO_BET unless confidence > override
CONFLICT_T2_DOWNGRADE = 0.65
# When consensus_quality in [T1, T2), allow PLAY only if confidence >= this
OVERRIDE_CONFIDENCE_WHEN_BELOW_T2 = 0.78

# -----------------------------------------------------------------------------
# Hard gate thresholds (quality gates)
# -----------------------------------------------------------------------------
# Evidence pack / domain quality score below this => NO_PREDICTION
THRESHOLD_EVIDENCE_QUALITY = 0.5

# Soft gate: max number of "minor" flags before downgrade to NO_BET
MAX_MINOR_FLAGS_BEFORE_NO_BET = 2

# -----------------------------------------------------------------------------
# Type aliases for request/response (optional; for clarity)
# -----------------------------------------------------------------------------
AnalyzerVersionLiteral = Literal["v1", "v2"]
