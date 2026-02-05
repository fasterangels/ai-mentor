"""
Report retention CLI: deterministic cleanup keeping last N reports.
Usage: python tools/report_retention_cli.py [--reports-dir reports] [--keep 200] [--dry-run]
Env: REPORT_RETENTION_COUNT (default 200), REPORT_RETENTION_DRY_RUN (default true).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from limits.retention import cleanup_reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Report retention: keep last N reports, prune rest (under reports dir only)")
    parser.add_argument("--reports-dir", default="reports", help="Reports directory (default: reports)")
    parser.add_argument("--keep", type=int, default=None, help="Keep last N runs (default: REPORT_RETENTION_COUNT or 200)")
    parser.add_argument("--dry-run", action="store_true", help="Do not delete; only list paths that would be removed")
    parser.add_argument("--no-dry-run", action="store_true", help="Actually delete (overrides REPORT_RETENTION_DRY_RUN)")
    args = parser.parse_args()

    import os
    env_dry = os.environ.get("REPORT_RETENTION_DRY_RUN", "").strip().lower() in ("1", "true", "yes")
    dry_run = args.dry_run or (not args.no_dry_run and env_dry)

    index, deleted_paths, errors = cleanup_reports(
        args.reports_dir,
        keep_last_n=args.keep,
        dry_run=dry_run,
    )
    if deleted_paths:
        for p in deleted_paths:
            print(p)
    if errors:
        print(f"Errors: {errors}", file=sys.stderr)
    return min(errors, 255) if errors else 0


if __name__ == "__main__":
    sys.exit(main())
