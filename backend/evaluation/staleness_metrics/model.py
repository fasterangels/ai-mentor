"""
Data structures for staleness metrics (G4). Stable sort order for deterministic output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class StalenessRow:
    """
    One row of staleness metrics: (market, reason_code, age_band).
    Sort key for stable ordering: (market, reason_code, age_band).
    """
    market: str
    reason_code: str
    age_band: str
    total: int
    correct: int
    neutral: int
    avg_confidence: float | None

    def _accuracy(self) -> float | None:
        resolved = self.correct + (self.total - self.correct - self.neutral)
        if resolved <= 0:
            return None
        return self.correct / resolved

    def _neutral_rate(self) -> float | None:
        if self.total <= 0:
            return None
        return self.neutral / self.total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market,
            "reason_code": self.reason_code,
            "age_band": self.age_band,
            "total": self.total,
            "correct": self.correct,
            "neutral": self.neutral,
            "accuracy": round(self._accuracy(), 4) if self._accuracy() is not None else None,
            "neutral_rate": round(self._neutral_rate(), 4) if self._neutral_rate() is not None else None,
            "avg_confidence": round(self.avg_confidence, 4) if self.avg_confidence is not None else None,
        }

    def sort_key(self) -> tuple[str, str, str]:
        """Stable ordering: market, reason_code, age_band."""
        return (self.market, self.reason_code, self.age_band)


@dataclass
class StalenessReport:
    """In-memory staleness report. Rows in deterministic order (market, reason_code, age_band)."""
    rows: List[StalenessRow]
    computed_at_utc: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "computed_at_utc": self.computed_at_utc,
            "notes": self.notes,
        }
