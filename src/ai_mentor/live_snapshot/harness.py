"""
Live snapshot harness stub: gate on env flags, write only under safe_snapshot_path.
No network calls.
"""

from __future__ import annotations

import os
import json
from datetime import datetime, timezone

from ai_mentor.utils.snapshot_paths import safe_snapshot_path
from ai_mentor.live_snapshot.live_connector_stub import LiveIODisabledError


def run_live_snapshot(run_id: str, filenames: list[str] | None = None) -> dict:
    """
    Run the live snapshot harness stub. Requires LIVE_IO_ALLOWED and SNAPSHOT_WRITES_ALLOWED.
    Writes JSON stub files only under reports/snapshots via safe_snapshot_path.
    """
    live_allowed = os.environ.get("LIVE_IO_ALLOWED", "").strip().lower() == "true"
    writes_allowed = os.environ.get("SNAPSHOT_WRITES_ALLOWED", "").strip().lower() == "true"

    if not live_allowed:
        raise LiveIODisabledError("LIVE_IO_ALLOWED is false")
    if not writes_allowed:
        raise PermissionError("SNAPSHOT_WRITES_ALLOWED is false")

    if filenames is None:
        filenames = ["snapshot_stub.json"]

    created_at = datetime.now(timezone.utc).isoformat()
    written_files: list[str] = []

    for filename in filenames:
        path = safe_snapshot_path(run_id, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "note": "live snapshot harness stub",
            "run_id": run_id,
            "created_at": created_at,
            "filename": filename,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        written_files.append(path)

    return {
        "run_id": run_id,
        "written_files": written_files,
        "note": "stub-only",
    }
