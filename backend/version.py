"""
Single source of version: read from repo root VERSION file.
Used by API and by CLI (tools/ops.py can use this or read VERSION directly).
"""

from __future__ import annotations

import re
from pathlib import Path


def _version_file_path() -> Path:
    # backend/version.py -> repo root
    return Path(__file__).resolve().parent.parent / "VERSION"


def get_version() -> str:
    """Return version string from VERSION file, or '0.0.0' if missing/invalid."""
    path = _version_file_path()
    if not path.is_file():
        return "0.0.0"
    try:
        raw = path.read_text(encoding="utf-8").strip()
        return raw.splitlines()[0].strip() if raw else "0.0.0"
    except OSError:
        return "0.0.0"


# Semantic version pattern (major.minor.patch, optional -pre)
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")


def is_semver(s: str) -> bool:
    """Return True if s matches semantic version pattern (e.g. 1.0.0 or 1.0.0-alpha)."""
    return bool(s and SEMVER_PATTERN.match(s.strip()))
