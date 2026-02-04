"""
Quality audit CLI: run decision quality deep-audit over stored snapshots/resolutions.
Usage: python tools/quality_audit.py [--last-n N] [--date-from ISO] [--date-to ISO] [--output-dir reports]
Outputs reports/quality_audit/<run_id>.json and appends summary to reports/index.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import models  # noqa: F401
from core.config import get_settings
from core.database import init_database, dispose_database, get_database_manager
from offline_eval.decision_quality import compute_decision_quality_report, load_history_from_session
from reports.index_store import append_quality_audit_run, load_index, save_index


def _run_id() -> str:
    return f"quality_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _parse_utc(s: str | None) -> datetime | None:
    if not s or not s.strip():
        return None
    s = s.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Decision quality audit: reason decay, calibration, stability")
    parser.add_argument("--last-n", type=int, default=None, help="Use last N runs (overrides date range)")
    parser.add_argument("--date-from", default=None, help="From date (ISO8601)")
    parser.add_argument("--date-to", default=None, help="To date (ISO8601)")
    parser.add_argument("--output-dir", default="reports", help="Reports directory (default: reports)")
    args = parser.parse_args()

    from_utc = _parse_utc(args.date_from)
    to_utc = _parse_utc(args.date_to)
    limit = args.last_n if args.last_n is not None else 5000

    settings = get_settings()
    await init_database(settings.database_url)
    try:
        async with get_database_manager().session() as session:
            records = await load_history_from_session(
                session,
                from_utc=from_utc,
                to_utc=to_utc,
                limit=limit,
            )
    finally:
        await dispose_database()

    report = compute_decision_quality_report(records)

    run_id = _run_id()
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
    payload = {
        "run_id": run_id,
        "created_at_utc": created_at,
        "run_count": len(records),
        "params": {"last_n": args.last_n, "date_from": args.date_from, "date_to": args.date_to, "limit": limit},
        "report": report,
    }

    output_dir = Path(args.output_dir)
    out_subdir = output_dir / "quality_audit"
    out_subdir.mkdir(parents=True, exist_ok=True)
    report_path = out_subdir / f"{run_id}.json"
    report_path.write_text(_stable_json(payload), encoding="utf-8")

    index_path = output_dir / "index.json"
    index = load_index(index_path)
    append_quality_audit_run(index, {
        "run_id": run_id,
        "created_at_utc": created_at,
        "run_count": len(records),
        "summary": report.get("summary", {}),
    })
    save_index(index, index_path)

    print(f"{run_id},{report_path}")
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
