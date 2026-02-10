"""
Live snapshot harness entry: check LIVE_IO_ALLOWED and SNAPSHOT_WRITES_ALLOWED; return stub result or raise.
"""

from __future__ import annotations

import os

from ingestion.live_io import LiveIODisabledError


def run_live_snapshot_harness() -> dict:
    """
    If LIVE_IO_ALLOWED or SNAPSHOT_WRITES_ALLOWED is false, raise LiveIODisabledError.
    Otherwise return gates_passed with stub connector name.
    """
    live_ok = os.environ.get("LIVE_IO_ALLOWED", "").strip().lower() in ("1", "true", "yes")
    writes_ok = os.environ.get("SNAPSHOT_WRITES_ALLOWED", "").strip().lower() in ("1", "true", "yes")
    if not live_ok:
        raise LiveIODisabledError("LIVE_IO_ALLOWED is false or unset")
    if not writes_ok:
        raise LiveIODisabledError("SNAPSHOT_WRITES_ALLOWED is false or unset")
    return {"status": "gates_passed", "connector": "live_connector_stub"}
