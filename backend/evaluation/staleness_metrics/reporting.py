"""
Staleness report writers (G4). Stable ordering; deterministic output.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

# Columns for CSV; order is stable.
CSV_FIELDNAMES = [
    "market",
    "reason_code",
    "age_band",
    "total",
    "correct",
    "accuracy",
    "neutral_rate",
    "avg_confidence",
]


def write_csv(report: Dict[str, Any], path: str | Path) -> None:
    """
    Write staleness report rows to CSV. Report must have "rows" (list of dicts).
    Rows are written in existing order (assumed stable: market, reason_code, age_band).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = report.get("rows") or []
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in CSV_FIELDNAMES})


def write_json(report: Dict[str, Any], path: str | Path) -> None:
    """
    Write full staleness report to JSON. Stable key order (sort_keys=True).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, sort_keys=True, indent=2, default=str),
        encoding="utf-8",
    )
