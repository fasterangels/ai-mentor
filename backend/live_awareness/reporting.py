"""
Write live awareness state to JSON with stable key ordering.
No runner yet (Part B); reporting only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .model import LiveAwarenessState


def state_to_dict(state: LiveAwarenessState) -> Dict[str, Any]:
    """Convert LiveAwarenessState to a dict with stable key order for JSON."""
    return {
        "schema_version": state.schema_version,
        "computed_at_utc": state.computed_at_utc.isoformat(),
        "scope_id": state.scope_id,
        "has_live_shadow": state.has_live_shadow,
        "latest_live_observed_at_utc": state.latest_live_observed_at_utc,
        "latest_recorded_observed_at_utc": state.latest_recorded_observed_at_utc,
        "observed_gap_ms": state.observed_gap_ms,
        "notes": state.notes,
    }


def write_live_awareness_json(state: LiveAwarenessState, path: str | Path) -> None:
    """Write state to JSON file with stable key ordering (explicit order, no sort_keys)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = state_to_dict(state)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def state_to_md(state: LiveAwarenessState) -> str:
    """Short human-readable summary for live_awareness.md."""
    lines = [
        "# Live Awareness",
        "",
        f"**Scope:** {state.scope_id}",
        f"**Has live shadow:** {state.has_live_shadow}",
        "",
        f"Computed at (UTC): {state.computed_at_utc.isoformat()}",
        "",
    ]
    if state.latest_recorded_observed_at_utc:
        lines.append(f"- Latest recorded: {state.latest_recorded_observed_at_utc}")
    if state.latest_live_observed_at_utc:
        lines.append(f"- Latest live shadow: {state.latest_live_observed_at_utc}")
    if state.observed_gap_ms is not None:
        lines.append(f"- Observed gap (live − recorded): {state.observed_gap_ms} ms")
    if state.notes:
        lines.append(f"- Notes: {state.notes}")
    lines.append("")
    return "\n".join(lines)


def write_live_awareness_md(state: LiveAwarenessState, path: str | Path) -> None:
    """Write short human summary to live_awareness.md."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state_to_md(state), encoding="utf-8")
