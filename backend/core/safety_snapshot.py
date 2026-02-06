"""
Bounded safety flags snapshot for report/ops. Same contract as src/ai_mentor/safety/defaults.
Used at report generation time; does not replace existing config.
"""

from __future__ import annotations

import os
from typing import Any, Dict


def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if not v:
        return default
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    return default


def safety_defaults_snapshot() -> Dict[str, Any]:
    """Return current safety flag values (booleans). Keys always present."""
    return {
        "LIVE_IO_ALLOWED": _env_bool("LIVE_IO_ALLOWED", False),
        "SNAPSHOT_WRITES_ALLOWED": _env_bool("SNAPSHOT_WRITES_ALLOWED", False),
        "SNAPSHOT_REPLAY_ENABLED": _env_bool("SNAPSHOT_REPLAY_ENABLED", False),
        "INJ_NEWS_ENABLED": _env_bool("INJ_NEWS_ENABLED", False),
        "INJ_NEWS_SHADOW_ATTACH_ENABLED": _env_bool("INJ_NEWS_SHADOW_ATTACH_ENABLED", False),
    }


def safety_summary_for_report() -> Dict[str, Any]:
    """Bounded safety_summary for pipeline report."""
    return {
        "flags": safety_defaults_snapshot(),
        "note": "All unsafe modes require explicit opt-in",
    }
