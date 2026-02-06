"""
Recorded snapshot replay runner: read-only from reports/snapshots, produce shadow report.
No live IO. No network. Deterministic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ai_mentor.utils.snapshot_paths import ALLOWED_SNAPSHOT_BASE


def _snapshot_dir_allowed(snapshot_dir: str) -> Path:
    """Resolve snapshot_dir and ensure it is under ALLOWED_SNAPSHOT_BASE. Raise ValueError if not."""
    base = Path(ALLOWED_SNAPSHOT_BASE).resolve()
    candidate = Path(snapshot_dir).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        raise ValueError(
            "snapshot_dir must be under {}; got {!r}".format(
                ALLOWED_SNAPSHOT_BASE, snapshot_dir
            )
        ) from None
    if not candidate.is_dir():
        raise ValueError("snapshot_dir is not a directory: {!r}".format(snapshot_dir))
    return candidate


def replay_from_snapshots(snapshot_dir: str) -> dict:
    """
    Read recorded snapshots from snapshot_dir (must be under reports/snapshots),
    load all *.json deterministically (sorted), build recorded_inputs, produce a shadow report.
    Returns summary: snapshots_used, note, report_path.
    """
    resolved_dir = _snapshot_dir_allowed(snapshot_dir)
    json_files = sorted(resolved_dir.glob("*.json"))
    recorded_inputs: list[dict] = []
    for path in json_files:
        with open(path, encoding="utf-8") as f:
            recorded_inputs.append(json.load(f))

    report_name = "replay_report.json"
    report_path = resolved_dir / report_name
    report_payload = {
        "note": "recorded replay",
        "snapshots_used": len(recorded_inputs),
        "recorded_inputs": recorded_inputs,
        "snapshot_dir": str(resolved_dir),
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, sort_keys=True, indent=2)

    return {
        "snapshots_used": len(recorded_inputs),
        "note": "recorded replay",
        "report_path": str(report_path.resolve()),
    }
