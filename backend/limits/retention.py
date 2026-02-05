"""
Report retention: deterministic cleanup keeping last N reports.
Never deletes outside the reports directory. Supports dry-run.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from reports.index_store import load_index, save_index

# Config: keep last N report runs (conservative default)
DEFAULT_REPORT_RETENTION_COUNT = 200


def _retention_count() -> int:
    try:
        return int(os.environ.get("REPORT_RETENTION_COUNT", str(DEFAULT_REPORT_RETENTION_COUNT)))
    except ValueError:
        return DEFAULT_REPORT_RETENTION_COUNT


def _dry_run_default() -> bool:
    return os.environ.get("REPORT_RETENTION_DRY_RUN", "").strip().lower() in ("1", "true", "yes")


# Index list keys that hold run entries with run_id
_RUN_LIST_KEYS = (
    "runs",
    "live_shadow_runs",
    "live_shadow_analyze_runs",
    "activation_runs",
    "burn_in_runs",
    "provider_parity_runs",
    "quality_audit_runs",
    "burn_in_ops_runs",
    "tuning_plan_runs",
)

# Subdirs under reports_dir that contain run artifacts: subdir -> is_dir (True = directory per run_id, False = file run_id.json)
_ARTIFACT_SUBDIRS = (
    ("burn_in", True),   # burn_in/<run_id>/
    ("live_shadow_compare", False),  # live_shadow_compare/<run_id>.json
)


def _collect_run_ids(index: Dict[str, Any]) -> List[str]:
    """Collect all run_ids from index run lists; deterministic sort."""
    seen: Set[str] = set()
    for key in _RUN_LIST_KEYS:
        runs = index.get(key)
        if isinstance(runs, list):
            for entry in runs:
                if isinstance(entry, dict):
                    rid = entry.get("run_id")
                    if isinstance(rid, str) and rid:
                        seen.add(rid)
    return sorted(seen)


def _safe_under_root(path: Path, root: Path) -> bool:
    """True iff path resolves to a path under root (no traversal outside)."""
    try:
        r = root.resolve()
        p = path.resolve()
        return p == r or str(p).startswith(str(r) + os.sep)
    except (OSError, ValueError):
        return False


def cleanup_reports(
    reports_dir: str | Path,
    keep_last_n: int | None = None,
    dry_run: bool | None = None,
    index_path: str | Path | None = None,
) -> Tuple[Dict[str, Any], List[str], int]:
    """
    Prune report artifacts and index to keep last N runs (by run_id order).
    Never deletes paths outside reports_dir. Returns (updated_index, deleted_paths, error_count).

    - keep_last_n: default from REPORT_RETENTION_COUNT (200).
    - dry_run: if True, no deletion; default from REPORT_RETENTION_DRY_RUN (true).
    - index_path: default reports_dir/index.json.
    """
    reports_path = Path(reports_dir).resolve()
    if keep_last_n is None:
        keep_last_n = _retention_count()
    if dry_run is None:
        dry_run = _dry_run_default()
    idx_path = Path(index_path or reports_path / "index.json")
    if not idx_path.is_absolute():
        idx_path = reports_path / idx_path.name

    index = load_index(idx_path)
    all_run_ids = _collect_run_ids(index)
    if len(all_run_ids) <= keep_last_n:
        return index, [], 0

    to_remove_ids = set(all_run_ids[:-keep_last_n])
    kept_ids = set(all_run_ids[-keep_last_n:])
    deleted_paths: List[str] = []
    error_count = 0

    # Delete artifacts only under reports_path
    for run_id in sorted(to_remove_ids):
        for subdir, is_dir in _ARTIFACT_SUBDIRS:
            if is_dir:
                candidate = reports_path / subdir / run_id
            else:
                candidate = reports_path / subdir / f"{run_id}.json"
            if not candidate.exists():
                continue
            if not _safe_under_root(candidate, reports_path):
                error_count += 1
                continue
            deleted_paths.append(str(candidate))
            if not dry_run:
                try:
                    if candidate.is_dir():
                        shutil.rmtree(candidate)
                    else:
                        candidate.unlink()
                except OSError:
                    error_count += 1

    # Prune index lists: keep only entries whose run_id is in kept_ids; set latest_* from pruned list
    _latest_key_map = {
        "runs": "latest_run_id",
        "live_shadow_runs": "latest_live_shadow_run_id",
        "live_shadow_analyze_runs": "latest_live_shadow_analyze_run_id",
        "activation_runs": "latest_activation_run_id",
        "burn_in_runs": "latest_burn_in_run_id",
        "provider_parity_runs": "latest_provider_parity_run_id",
        "quality_audit_runs": "latest_quality_audit_run_id",
        "burn_in_ops_runs": "latest_burn_in_ops_run_id",
        "tuning_plan_runs": "latest_tuning_plan_run_id",
    }
    for key in _RUN_LIST_KEYS:
        runs = index.get(key)
        if isinstance(runs, list):
            index[key] = [e for e in runs if isinstance(e, dict) and e.get("run_id") in kept_ids]
        latest_key = _latest_key_map.get(key)
        if latest_key:
            runs = index.get(key)
            if isinstance(runs, list) and runs:
                index[latest_key] = runs[-1].get("run_id")
            else:
                index[latest_key] = None

    if not dry_run and idx_path.exists() and _safe_under_root(idx_path, reports_path):
        save_index(index, idx_path)

    return index, deleted_paths, error_count
