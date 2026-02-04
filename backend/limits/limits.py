"""
Hard limits & quotas: max batch matches (Phase 6 cap), max reports in index with pruning.
Burn-in ops: configurable max report bundles with deterministic pruning logged in index.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Reuse Phase 6 cap
MAX_MATCHES_PER_RUN = 50

# Max report entries retained in index; prune oldest deterministically
MAX_REPORTS_RETAINED = 100

# Max burn-in ops report bundles to keep on disk (prune oldest; log in index)
MAX_BURN_IN_OPS_BUNDLES = 30


def prune_index(index: Dict[str, Any], max_retained: int = MAX_REPORTS_RETAINED) -> Dict[str, Any]:
    """
    Prune index to keep at most max_retained runs (newest). Mutates and returns index.
    Order: runs are appended in chronological order, so oldest are at index 0; drop from front.
    """
    runs: List[Dict[str, Any]] = index.get("runs") or []
    if len(runs) <= max_retained:
        return index
    index["runs"] = runs[-max_retained:]
    if index["runs"]:
        index["latest_run_id"] = index["runs"][-1].get("run_id")
    else:
        index["latest_run_id"] = None
    return index


def prune_burn_in_ops_bundles(
    burn_in_dir: Path,
    index: Dict[str, Any],
    max_retained: int = MAX_BURN_IN_OPS_BUNDLES,
) -> Dict[str, Any]:
    """
    Prune burn_in report bundles: keep at most max_retained newest (by run_id order).
    Deterministic: sort run_id dirs, remove oldest. Log each pruned run_id in index.
    Mutates index and returns it.
    """
    burn_in_path = Path(burn_in_dir)
    if not burn_in_path.exists() or not burn_in_path.is_dir():
        return index
    run_dirs = sorted([d.name for d in burn_in_path.iterdir() if d.is_dir()])
    if len(run_dirs) <= max_retained:
        return index
    to_remove = run_dirs[:-max_retained]
    log = index.get("burn_in_ops_prune_log")
    if not isinstance(log, list):
        log = []
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
    for run_id in to_remove:
        dir_path = burn_in_path / run_id
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
            except OSError:
                pass
        log.append({"pruned_run_id": run_id, "pruned_at_utc": now})
    index["burn_in_ops_prune_log"] = log
    return index
