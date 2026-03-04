"""
Safe paths under a base directory for snapshot files; rejects traversal and empty components.
"""

from __future__ import annotations

from pathlib import Path

SNAPSHOTS_BASE_DIR = "snapshots"


def safe_snapshot_path(run_id: str, filename: str) -> Path:
    """
    Return a path under SNAPSHOTS_BASE_DIR for the given run_id and filename.
    Raises ValueError for traversal (..), path separators in run_id/filename, or empty components.
    """
    if not run_id or run_id.strip() != run_id:
        raise ValueError("Invalid run_id: empty or whitespace")
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise ValueError("Invalid run_id: path traversal or separators not allowed")
    if not filename or filename.strip() != filename:
        raise ValueError("Invalid filename: empty or whitespace")
    if ".." in filename or "/" in filename or "\\" in filename or filename != Path(filename).name:
        raise ValueError("Invalid filename: path traversal or separators not allowed")
    return Path(SNAPSHOTS_BASE_DIR) / run_id / filename
