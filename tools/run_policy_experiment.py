#!/usr/bin/env python3
"""
CLI tool to run decision policy experiments on an offline evaluation report.

Usage:
  python tools/run_policy_experiment.py path/to/report.json --objective precision --min-coverage 0.2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_BACKEND = _REPO_ROOT / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from backend.experiments.policy_experiment_runner import (  # type: ignore[import-error]
    ExperimentConfig,
    run_from_report_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run decision policy experiment on an evaluation report.")
    parser.add_argument("report_path", help="Path to evaluation_report.json")
    parser.add_argument(
        "--objective",
        choices=["precision", "f1"],
        default="precision",
        help="Objective to optimize (precision or f1).",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.20,
        help="Minimum GO coverage required (fraction between 0 and 1).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = ExperimentConfig(
        objective=args.objective,
        min_coverage=args.min_coverage,
    )
    result = run_from_report_path(args.report_path, cfg)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

