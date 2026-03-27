"""
Path-safe snapshot helper: guarantees snapshot writes are restricted to the allowed base directory.
No filesystem writes; validation and path construction only.
"""

from __future__ import annotations

import re
from pathlib import Path

ALLOWED_SNAPSHOT_BASE = "reports/snapshots"

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def safe_snapshot_path(run_id: str, filename: str) -> str:
    """
    Build a validated path under ALLOWED_SNAPSHOT_BASE for the given run_id and filename.
    run_id must be non-empty and match ^[A-Za-z0-9_-]{6,64}$.
    filename must be non-empty, contain no path separators, and match ^[A-Za-z0-9_.-]{1,128}$.
    Returns the normalized absolute path as a string, guaranteed to be within the resolved base dir.
    """
    if not run_id or not _RUN_ID_RE.match(run_id):
        raise ValueError(
            "run_id must be non-empty and match ^[A-Za-z0-9_-]{6,64}$"
        )
    if not filename or "/" in filename or "\\" in filename:
        raise ValueError(
            "filename must be non-empty and must not contain path separators"
        )
    if not _FILENAME_RE.match(filename):
        raise ValueError(
            "filename must match ^[A-Za-z0-9_.-]{1,128}$"
        )
    base = Path(ALLOWED_SNAPSHOT_BASE).resolve()
    combined = base / run_id / filename
    resolved = combined.resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(
            "Path would escape base dir: run_id={!r} filename={!r}".format(
                run_id, filename
            )
        ) from None
    return str(resolved)
