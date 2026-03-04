"""
Operational CLI: one command to run full shadow batch, save report under reports/,
update reports/index.json, and print guardrail alert summary.
Usage: python tools/operational_run.py [--connector dummy] [--output-dir reports] [--match-ids ...] [--now-utc ISO8601]
Exit 0 always (operational); alerts included in report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path when run from repo root
_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import models  # noqa: F401 - register models
from core.config import get_settings
from core.database import init_database, dispose_database, get_database_manager
from runner.shadow_runner import run_shadow_batch
from reports.alerts import evaluate_alerts
from reports.index_store import (
    append_activation_run,
    append_burn_in_run,
    load_index,
    append_run,
    save_index,
)
from limits.limits import prune_index


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _normalize_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.replace(microsecond=0)


def _parse_now_utc(s: str | None) -> datetime | None:
    if not s or not s.strip():
        return None
    dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    return _normalize_utc(dt)


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Operational run: shadow batch + report + index, or refusal-optimize-shadow")
    parser.add_argument("--mode", default=None, choices=["refusal-optimize-shadow"], help="Run mode (default: shadow batch)")
    parser.add_argument("--connector", default="dummy", help="Connector name (default: dummy)")
    parser.add_argument("--output-dir", default="reports", help="Reports directory (default: reports)")
    parser.add_argument("--match-ids", default=None, help="Optional comma-separated match IDs")
    parser.add_argument("--now-utc", default=None, help="Optional ISO8601 time for determinism")
    parser.add_argument("--dry-run", action="store_true", help="Do not persist SnapshotResolution or write cache")
    parser.add_argument("--activation", action="store_true", help="Enable activation (respects env gates)")
    args = parser.parse_args()

    if getattr(args, "mode", None) == "refusal-optimize-shadow":
        from runner.refusal_optimization_runner import run_refusal_optimization
        result = run_refusal_optimization(reports_dir=args.output_dir)
        paths = result.get("artifact_paths") or []
        print("refusal_optimize_shadow", ",".join(paths), result.get("decisions_count", 0))
        return 0

    now = _parse_now_utc(args.now_utc)
    if now is None:
        now = datetime.now(timezone.utc).replace(microsecond=0)

    match_ids = None
    if args.match_ids:
        match_ids = [m.strip() for m in args.match_ids.split(",") if m.strip()]

    settings = get_settings()
    await init_database(settings.database_url)

    try:
        async with get_database_manager().session() as session:
            batch_report = await run_shadow_batch(
                session,
                connector_name=args.connector,
                match_ids=match_ids,
                now_utc=now,
                dry_run=args.dry_run,
                activation=args.activation,
            )
    finally:
        await dispose_database()

    alerts = evaluate_alerts(batch_report)
    alerts_count = len(alerts)

    # Report payload includes batch report + alerts
    full_report = {**batch_report, "alerts": alerts}

    # Filename: shadow_batch_<YYYYMMDD_HHMMSS>_<shortchecksum>.json
    ts_part = now.strftime("%Y%m%d_%H%M%S")
    checksums = batch_report.get("checksums") or {}
    out_checksum = checksums.get("batch_output_checksum") or checksums.get("batch_input_checksum") or "00000000"
    short_checksum = (out_checksum or "00000000")[:8]
    report_filename = f"shadow_batch_{ts_part}_{short_checksum}.json"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / report_filename
    report_path.write_text(_stable_json(full_report), encoding="utf-8")

    # Index entry
    run_meta_batch = batch_report.get("run_meta") or {}
    run_id = report_path.stem  # shadow_batch_YYYYMMDD_HHMMSS_shortchecksum
    live_io_alerts = batch_report.get("live_io_alerts") or []
    index_run_meta = {
        "run_id": run_id,
        "created_at_utc": run_meta_batch.get("started_at_utc") or now.isoformat(),
        "connector_name": run_meta_batch.get("connector_name") or args.connector,
        "matches_count": run_meta_batch.get("matches_count", 0) if run_meta_batch else 0,
        "batch_output_checksum": checksums.get("batch_output_checksum"),
        "alerts_count": alerts_count,
        "live_io_alerts_count": len(live_io_alerts),
    }

    index_path = output_dir / "index.json"
    index = load_index(index_path)
    append_run(index, index_run_meta)
    activation_summary = batch_report.get("activation") or {}
    if args.activation and activation_summary:
        append_activation_run(index, {
            "run_id": run_id,
            "created_at_utc": index_run_meta.get("created_at_utc"),
            "connector_name": index_run_meta.get("connector_name"),
            "matches_count": index_run_meta.get("matches_count", 0),
            "activated": activation_summary.get("activated", False),
            "reason": activation_summary.get("reason"),
            "activation_summary": activation_summary,
        })
    burn_in_section = activation_summary.get("burn_in")
    if args.activation and burn_in_section:
        append_burn_in_run(index, {
            "run_id": run_id,
            "created_at_utc": index_run_meta.get("created_at_utc"),
            "connector_name": index_run_meta.get("connector_name"),
            "matches_count": index_run_meta.get("matches_count", 0),
            "burn_in_summary": burn_in_section,
        })
    prune_index(index)
    save_index(index, index_path)

    # Output clearly indicates dry_run when set
    if batch_report.get("dry_run"):
        print("dry_run=true", end=" ")
    print(f"{run_id},{report_path},{alerts_count}")
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
