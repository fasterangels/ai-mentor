"""
Hard limits & quotas: max batch matches (Phase 6 cap), max reports in index with pruning.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Reuse Phase 6 cap
MAX_MATCHES_PER_RUN = 50

# Max report entries retained in index; prune oldest deterministically
MAX_REPORTS_RETAINED = 100


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
