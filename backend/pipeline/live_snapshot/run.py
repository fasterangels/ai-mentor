"""
Live snapshot harness runner: safety gates and stub connector.
No network; OFF by default. Fails fast when LIVE_IO_ALLOWED or SNAPSHOT_WRITES_ALLOWED are false.
"""

from __future__ import annotations

from ingestion.live_io import (
    LiveIODisabledError,
    live_io_allowed,
    snapshot_writes_allowed,
)
from ops.ops_events import log_guardrail_trigger

from pipeline.live_snapshot.stub_connector import LiveConnectorStub


def run_live_snapshot_harness(*, connector=None):
    """
    Run the live snapshot harness skeleton. Internal/CLI only; not an API endpoint.
    Requires LIVE_IO_ALLOWED=true and SNAPSHOT_WRITES_ALLOWED=true or fails fast with ops event.
    Uses LiveConnectorStub by default (no network; stub raises on fetch if used).
    Returns a small dict with status when gates pass; does not perform fetch by default.
    """
    if not live_io_allowed():
        log_guardrail_trigger(
            trigger="live_snapshot_harness_disabled",
            detail="LIVE_IO_ALLOWED is not true; set LIVE_IO_ALLOWED=true to run harness",
        )
        raise LiveIODisabledError(
            "Live snapshot harness is disabled: LIVE_IO_ALLOWED is not true. Set LIVE_IO_ALLOWED=true to run."
        )
    if not snapshot_writes_allowed():
        log_guardrail_trigger(
            trigger="live_snapshot_harness_disabled",
            detail="SNAPSHOT_WRITES_ALLOWED is not true; set SNAPSHOT_WRITES_ALLOWED=true to write snapshots",
        )
        raise LiveIODisabledError(
            "Live snapshot harness is disabled: SNAPSHOT_WRITES_ALLOWED is not true. Set SNAPSHOT_WRITES_ALLOWED=true to write snapshots."
        )
    c = connector if connector is not None else LiveConnectorStub()
    return {"status": "gates_passed", "connector": c.name}
