"""
Live->snapshot harness skeleton (shadow-only, no network by default).
Harness is OFF by default; requires LIVE_IO_ALLOWED and SNAPSHOT_WRITES_ALLOWED.
Uses stub connector that fails fast; no network calls.
G1: Live read adapter (live_shadow) reads via LiveSourceClient and writes snapshots only.
"""

from pipeline.live_snapshot.live_shadow_adapter import run_live_shadow_read, run_live_shadow_read_blocked_or_raise
from pipeline.live_snapshot.live_source_client import FakeLiveClient, NullLiveClient
from pipeline.live_snapshot.run import run_live_snapshot_harness
from pipeline.live_snapshot.snapshot_path import SNAPSHOTS_BASE_DIR, safe_snapshot_path

__all__ = [
    "run_live_snapshot_harness",
    "run_live_shadow_read",
    "run_live_shadow_read_blocked_or_raise",
    "FakeLiveClient",
    "NullLiveClient",
    "SNAPSHOTS_BASE_DIR",
    "safe_snapshot_path",
]
