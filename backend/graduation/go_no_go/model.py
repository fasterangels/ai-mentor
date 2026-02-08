"""Go/No-Go decision model: formal artifact derived from J1 graduation result."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class GoNoGoDecision:
    """
    Go/No-Go decision derived strictly from J1 graduation result.
    No automation; authorization to proceed to future planning only when GO.
    """

    schema_version: int
    decision: str  # "GO" | "NO_GO"
    decision_time_utc: datetime
    graduation_ref: Optional[str]  # referenced_graduation_result_path
    failed_criteria: List[Dict[str, Any]]  # name + details for each failed criterion (when NO_GO)
    warnings: List[str]  # optional; when GO, derived from criterion details only
