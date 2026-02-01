"""Policy defaults and constants for analyzer v1."""

from .types import AnalyzerPolicy

# Default policy configuration
default_policy = AnalyzerPolicy(
    min_sep_1x2=0.10,
    min_sep_ou=0.08,
    min_sep_gg=0.08,
    min_confidence=0.62,
    risk_caps={"default": 0.35},
)

# Fixed constants for deterministic calculations
HOME_ADVANTAGE_BASE = 0.15  # Base home advantage boost
SOFTMAX_TEMPERATURE = 1.0  # Temperature for probability conversion
EXPECTED_GOALS_THRESHOLD = 2.5  # Threshold for OU25 market
MIN_EVIDENCE_QUALITY = 0.5  # Minimum quality score to proceed

# Critical flags that trigger NO_PREDICTION
CRITICAL_FLAGS = {
    "QUALITY_GATE_FAILED",
    "NO_SOURCES_AVAILABLE",
    "INSUFFICIENT_SOURCES",
}
