"""
CLI for deterministic shadow batch runner.
Usage: python tools/shadow_runner.py [--connector dummy] [--match-ids id1,id2] [--output shadow_batch_report.json]
Exits 0 even if some matches fail; failures are listed in the report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add backend to path when run from repo root
_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import models  # noqa: F401 - register models
from core.config import get_settings
from core.database import init_database, dispose_database, get_database_manager
from runner.shadow_runner import run_shadow_batch


def _stable_json(obj: object) -> str:
    """JSON with sorted keys for deterministic output."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run shadow batch and write report")
    parser.add_argument("--connector", default="dummy", help="Connector name (default: dummy)")
    parser.add_argument(
        "--match-ids",
        default=None,
        help="Optional comma-separated match IDs; if omitted, use all cached for connector",
    )
    parser.add_argument(
        "--output",
        default="shadow_batch_report.json",
        help="Output JSON file path (default: shadow_batch_report.json)",
    )
    args = parser.parse_args()

    match_ids = None
    if args.match_ids:
        match_ids = [m.strip() for m in args.match_ids.split(",") if m.strip()]

    settings = get_settings()
    await init_database(settings.database_url)

    try:
        async with get_database_manager().session() as session:
            report = await run_shadow_batch(
                session,
                connector_name=args.connector,
                match_ids=match_ids,
            )
    finally:
        await dispose_database()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_stable_json(report), encoding="utf-8")

    # Exit 0 even if some matches failed; failures are in report["failures"]
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
