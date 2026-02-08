"""
Snapshot path safety: single allowed base directory, path traversal prevention.
All snapshot writes must stay under reports/snapshots/.
"""

from __future__ import annotations

from pathlib import Path


SNAPSHOTS_BASE_DIR = "reports/snapshots"


def safe_snapshot_path(
    run_id: str,
    filename: str,
    *,
    base_dir: str | Path | None = None,
) -> Path:
    """
    Return a validated path under the allowed snapshots base directory.
    Resolves path, prevents traversal (..), ensures result is under base.
    Raises ValueError if run_id/filename would escape the base.
    """
    base = Path(base_dir) if base_dir is not None else Path(SNAPSHOTS_BASE_DIR)
    base = base.resolve()

    run_id_s = str(run_id).strip()
    filename_s = str(filename).strip()
    if not run_id_s or ".." in run_id_s or run_id_s.startswith("/"):
        raise ValueError("Invalid run_id: {!r}".format(run_id))
    if not filename_s or ".." in filename_s or filename_s.startswith("/"):
        raise ValueError("Invalid filename: {!r}".format(filename))

    combined = base / run_id_s / filename_s
    resolved = combined.resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(
            "Path would escape base dir: run_id={!r} filename={!r} -> {}".format(
                run_id, filename, resolved
            )
        ) from None
    return resolved
