"""
Read-only reports viewer: path traversal protection and optional token guard.
If REPORTS_READ_TOKEN is set, require X-Reports-Token header to match; otherwise allow (e.g. local use).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_reports_root() -> Path:
    """Reports directory root (env REPORTS_DIR or default 'reports'), resolved for current working directory."""
    raw = os.environ.get("REPORTS_DIR", "reports")
    return Path(raw).expanduser().resolve()


def reports_token_required() -> bool:
    """True if REPORTS_READ_TOKEN is set (token guard enabled)."""
    return bool(os.environ.get("REPORTS_READ_TOKEN", "").strip())


def check_reports_token(provided: Optional[str]) -> bool:
    """
    Return True if access is allowed: either no token is required, or provided matches REPORTS_READ_TOKEN.
    """
    expected = os.environ.get("REPORTS_READ_TOKEN", "").strip()
    if not expected:
        return True
    return bool(provided and provided.strip() == expected)


def safe_path_under_reports(reports_root: Path, relative_path: str) -> Optional[Path]:
    """
    Resolve relative_path under reports_root; allow only paths under reports_root (no traversal).
    Returns resolved Path if safe and under reports_root, else None. Caller checks is_file() for 404.
    """
    if not relative_path or not relative_path.strip():
        return None
    try:
        joined = (reports_root / relative_path.strip().lstrip("/")).resolve()
        root_resolved = reports_root.resolve()
        joined.relative_to(root_resolved)
        return joined
    except (ValueError, OSError, RuntimeError):
        return None
