"""
Uncertainty signal model (H3). Read-only; no refusals enforced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


# Signal type constants (documented, explicit)
STALE_EVIDENCE = "STALE_EVIDENCE"
CONFLICTING_REASONS = "CONFLICTING_REASONS"  # Skipped if polarity not available
LOW_EFFECTIVE_CONFIDENCE = "LOW_EFFECTIVE_CONFIDENCE"
LOW_SUPPORT = "LOW_SUPPORT"


@dataclass
class UncertaintySignal:
    """One uncertainty signal: type, short reason code, and whether it triggered."""
    signal_type: str
    reason_code: str  # Short explanation string
    triggered: bool

    def to_dict(self) -> dict:
        return {
            "reason_code": self.reason_code,
            "signal_type": self.signal_type,
            "triggered": self.triggered,
        }


@dataclass
class UncertaintyProfile:
    """Uncertainty profile per decision (run). List of signals; no enforcement."""
    run_id: str
    signals: List[UncertaintySignal]

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "signals": [s.to_dict() for s in self.signals],
        }
