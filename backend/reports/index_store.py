"""
Reports index: load/save index.json with stable JSON (sorted keys).
Index structure: runs (list of run entries), latest_run_id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _stable_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def load_index(path: str | Path = "reports/index.json") -> Dict[str, Any]:
    """
    Load index from path. Returns dict with keys: runs (list), latest_run_id (str or None).
    If file does not exist, returns empty index: {"runs": [], "latest_run_id": None}.
    """
    path = Path(path)
    if not path.exists():
        return {"runs": [], "latest_run_id": None}

    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    runs = data.get("runs")
    if not isinstance(runs, list):
        runs = []
    return {
        "runs": runs,
        "latest_run_id": data.get("latest_run_id"),
    }


def append_run(index: Dict[str, Any], run_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a run entry to the index and set latest_run_id.
    run_meta must include: run_id, created_at_utc, connector_name, matches_count,
    batch_output_checksum, alerts_count.
    Returns updated index (mutates and returns the same dict).
    """
    runs: List[Dict[str, Any]] = index.get("runs") or []
    entry = {
        "run_id": run_meta.get("run_id"),
        "created_at_utc": run_meta.get("created_at_utc"),
        "connector_name": run_meta.get("connector_name"),
        "matches_count": run_meta.get("matches_count"),
        "batch_output_checksum": run_meta.get("batch_output_checksum"),
        "alerts_count": run_meta.get("alerts_count"),
    }
    runs.append(entry)
    index["runs"] = runs
    index["latest_run_id"] = run_meta.get("run_id")
    return index


def save_index(index: Dict[str, Any], path: str | Path) -> None:
    """Persist index to path with stable JSON (sorted keys)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_dumps(index), encoding="utf-8")
