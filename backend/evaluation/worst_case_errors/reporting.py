"""
Write worst-case report to CSV and JSON with stable ordering.
Top N configurable (default 50); deterministic column/key order.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from .model import WorstCaseReport, WorstCaseRow

DEFAULT_TOP_N = 50

# Stable column order for CSV and keys for JSON rows
CSV_COLUMNS = [
    "fixture_id",
    "market",
    "prediction",
    "outcome",
    "original_confidence",
    "worst_case_score",
    "snapshot_type",
    "triggered_uncertainty_signals",
    "snapshot_ids",
]


def _row_to_dict(row: WorstCaseRow) -> dict:
    """Convert row to dict with stable key order; list fields as JSON strings for CSV."""
    return {
        "fixture_id": row.fixture_id,
        "market": row.market,
        "prediction": row.prediction,
        "outcome": row.outcome,
        "original_confidence": round(row.original_confidence, 4),
        "worst_case_score": round(row.worst_case_score, 4),
        "snapshot_type": row.snapshot_type or "",
        "triggered_uncertainty_signals": json.dumps(row.triggered_uncertainty_signals or [], sort_keys=True),
        "snapshot_ids": json.dumps(row.snapshot_ids or [], sort_keys=True),
    }


def write_csv(report: WorstCaseReport, path: str | Path, top_n: int = DEFAULT_TOP_N) -> None:
    """Write report rows (top N) to CSV with stable column order."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = report.rows[:top_n]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(_row_to_dict(row))


def write_json(report: WorstCaseReport, path: str | Path, top_n: int = DEFAULT_TOP_N) -> None:
    """Write report to JSON: computed_at_utc + rows (top N) with stable key order."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = report.rows[:top_n]
    payload = {
        "computed_at_utc": report.computed_at_utc.isoformat(),
        "top_n": top_n,
        "rows": [_row_to_dict(r) for r in rows],
    }
    # Deterministic dump
    text = json.dumps(payload, sort_keys=True, indent=2, default=str)
    path.write_text(text, encoding="utf-8")
