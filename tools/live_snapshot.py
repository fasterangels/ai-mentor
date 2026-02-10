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


async def _run_delta_eval() -> int:
    import models  # noqa: F401
    from core.config import get_settings
    from core.database import init_database, dispose_database, get_database_manager
    from runner.delta_eval_runner import run_delta_eval_mode

    settings = get_settings()
    await init_database(settings.database_url)
    try:
        async with get_database_manager().session() as session:
            result = await run_delta_eval_mode(session, reports_dir="reports")
        print(
            "delta-eval ok: reports_written=%s complete=%s incomplete=%s run_id=%s"
            % (
                result.get("reports_written", 0),
                result.get("complete_count", 0),
                result.get("incomplete_count", 0),
                result.get("run_id", ""),
            )
        )
        return 0
    finally:
        await dispose_database()


def _run_decay_fit() -> int:
    """Run decay-fit (H1): read G4 staleness JSON, fit params, write artifacts. No DB."""
    from runner.decay_fit_runner import run_decay_fit_mode

    result = run_decay_fit_mode(reports_dir="reports")
    if result.get("error"):
        print("decay-fit error:", result.get("error"), file=sys.stderr)
        return 1
    print(
        "decay-fit ok: params_count=%s skipped_low_support=%s path=%s"
        % (
            result.get("params_count", 0),
            result.get("skipped_low_support", 0),
            result.get("params_path", ""),
        )
    )
    return 0


async def _run_staleness_eval() -> int:
    import models  # noqa: F401
    from core.config import get_settings
    from core.database import init_database, dispose_database, get_database_manager
    from runner.staleness_eval_runner import run_staleness_eval_mode

    settings = get_settings()
    await init_database(settings.database_url)
    try:
        async with get_database_manager().session() as session:
            result = await run_staleness_eval_mode(session, reports_dir="reports")
        print(
            "staleness-eval ok: row_count=%s missing_ts=%s run_id=%s"
            % (
                result.get("row_count", 0),
                result.get("missing_timestamps_count", 0),
                result.get("run_id", ""),
            )
        )
        return 0
    finally:
        await dispose_database()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Live snapshot: harness, live-shadow (G1), delta-eval (G3), staleness-eval (G4), decay-fit (H1)"
    )
    parser.add_argument(
        "--mode",
        choices=["harness", "live-shadow", "delta-eval", "staleness-eval", "decay-fit"],
        default="harness",
        help="harness: gates only; live-shadow: fetch -> snapshots; delta-eval: live vs recorded; staleness-eval: metrics by reason/age; decay-fit: fit decay params from G4 metrics",
    )
    args = parser.parse_args()

    if args.mode == "live-shadow":
        return asyncio.run(_run_live_shadow())
    if args.mode == "delta-eval":
        return asyncio.run(_run_delta_eval())
    if args.mode == "staleness-eval":
        return asyncio.run(_run_staleness_eval())
    if args.mode == "decay-fit":
        return _run_decay_fit()
    return _run_harness()


if __name__ == "__main__":
    sys.exit(main())
