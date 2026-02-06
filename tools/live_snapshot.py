"""
CLI for live->snapshot harness and live-shadow mode (G1).
Default: harness (gates only). Use --mode live-shadow to run live read -> snapshot only.
Exits 1 when LIVE_IO_ALLOWED or SNAPSHOT_WRITES_ALLOWED are not set (expected default).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def _run_harness() -> int:
    from ingestion.live_io import LiveIODisabledError
    from pipeline.live_snapshot.run import run_live_snapshot_harness

    try:
        run_live_snapshot_harness()
        return 0
    except LiveIODisabledError as e:
        print("live_snapshot harness disabled:", e, file=sys.stderr)
        return 1


async def _run_live_shadow() -> int:
    import models  # noqa: F401
    from core.config import get_settings
    from core.database import init_database, dispose_database, get_database_manager
    from ingestion.live_io import LiveIODisabledError
    from pipeline.live_snapshot import (
        FakeLiveClient,
        run_live_shadow_read_blocked_or_raise,
    )
    from runner.live_shadow_runner import run_live_shadow_mode

    run_live_shadow_read_blocked_or_raise()
    settings = get_settings()
    await init_database(settings.database_url)
    try:
        async with get_database_manager().session() as session:
            client = FakeLiveClient()
            result = await run_live_shadow_mode(session, client)
        if result.get("error"):
            print(result.get("detail", result.get("error")), file=sys.stderr)
            return 1
        print(
            "live-shadow ok: snapshots_written=%s deduped=%s fetch_ok=%s fetch_failed=%s"
            % (
                result.get("snapshots_written", 0),
                result.get("deduped", 0),
                result.get("fetch_ok", 0),
                result.get("fetch_failed", 0),
            )
        )
        return 0
    except LiveIODisabledError as e:
        print("live-shadow disabled:", e, file=sys.stderr)
        return 1
    finally:
        await dispose_database()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Live snapshot: harness (default) or live-shadow mode (G1)"
    )
    parser.add_argument(
        "--mode",
        choices=["harness", "live-shadow"],
        default="harness",
        help="harness: gates only; live-shadow: fetch -> write snapshots (no analysis)",
    )
    args = parser.parse_args()

    if args.mode == "live-shadow":
        return asyncio.run(_run_live_shadow())
    return _run_harness()


if __name__ == "__main__":
    sys.exit(main())
