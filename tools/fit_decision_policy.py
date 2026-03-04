#!/usr/bin/env python3
"""
CLI tool to fit decision policy thresholds from an evaluation report.

Usage:
  python tools/fit_decision_policy.py path/to/report.json --policy-path backend/policies/decision_engine_policy.json --version v1 --objective precision --min-coverage 0.2 [--target-precision 0.7]
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

from backend.policies.fit_decision_engine_policy import (  # type: ignore[import-error]
    FitConfig,
    fit_and_save_policy_from_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit decision policy thresholds from an evaluation report.")
    parser.add_argument("report_path", help="Path to evaluation_report.json")
    parser.add_argument(
        "--policy-path",
        default="backend/policies/decision_engine_policy.json",
        help="Path to save the fitted policy JSON.",
    )
    parser.add_argument(
        "--version",
        default="v1",
        help="Policy version to write.",
    )
    parser.add_argument(
        "--objective",
        choices=["precision", "f1"],
        default="precision",
        help="Objective to optimize when target_precision is not set.",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.20,
        help="Minimum GO coverage required (fraction between 0 and 1).",
    )
    parser.add_argument(
        "--target-precision",
        type=float,
        default=None,
        help="Target precision to achieve; when set, use target-precision fitting.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = FitConfig(
        min_coverage=args.min_coverage,
        objective=args.objective,
        threshold_grid=None,
        target_precision=args.target_precision,
        version=args.version,
    )
    policy = fit_and_save_policy_from_report(args.report_path, args.policy_path, cfg)
    summary = {
        "version": policy.version,
        "thresholds": policy.thresholds,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

