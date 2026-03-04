#!/usr/bin/env python3
"""
CLI helper to build Decision Intelligence dashboard data from an evaluation report.

Usage:
  python tools/build_dashboard_data.py path/to/evaluation_report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_BACKEND = _REPO_ROOT / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
  sys.path.insert(0, str(_BACKEND))

from dashboard.dashboard_data import DashboardConfig, build_dashboard_data  # type: ignore[import-error]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: build_dashboard_data.py PATH_TO_REPORT_JSON", file=sys.stderr)
        raise SystemExit(1)

    report_path = Path(sys.argv[1])
    data = json.loads(report_path.read_text())
    cfg = DashboardConfig()
    dashboard = build_dashboard_data(data, cfg)
    print(json.dumps(dashboard, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

