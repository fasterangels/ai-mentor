#!/usr/bin/env python3
"""
Decision audit CLI: compare current vs proposed policy on snapshots;
write audit_report.json with per-market rows and summary.

Usage:
  python tools/decision_audit.py --snapshots path/to/snapshots.json --proposal path/to/proposal.json [--output audit_report.json] [--all]
  --all: include all rows (default: first 200)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _REPO_ROOT / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from policy.policy_model import Policy
from policy.policy_runtime import get_active_policy
from policy.audit import audit_snapshots

DEFAULT_ROWS_LIMIT = 200


def load_snapshots(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


def load_proposed_policy(path: Path) -> Policy:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "proposed_policy" in data:
        return Policy.model_validate(data["proposed_policy"])
    return Policy.model_validate(data)


def main() -> int:
    ap = argparse.ArgumentParser(description="Decision audit: current vs proposed policy on snapshots")
    ap.add_argument("--snapshots", type=Path, required=True, help="JSON: list of { match_id, evidence_pack }")
    ap.add_argument("--proposal", type=Path, required=True, help="JSON: proposal with proposed_policy or Policy")
    ap.add_argument("--output", type=Path, default=Path("audit_report.json"), help="Output report path")
    ap.add_argument("--all", action="store_true", help="Include all rows (default: first %d)" % DEFAULT_ROWS_LIMIT)
    args = ap.parse_args()

    snapshots = load_snapshots(args.snapshots)
    proposed_policy = load_proposed_policy(args.proposal)
    current_policy = get_active_policy()

    report = audit_snapshots(snapshots, current_policy, proposed_policy)

    if not args.all and report["rows"]:
        report["rows"] = report["rows"][:DEFAULT_ROWS_LIMIT]
        report["_rows_truncated"] = True
        report["_rows_limit"] = DEFAULT_ROWS_LIMIT
    else:
        report["_rows_truncated"] = False

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    s = report["summary"]
    print(f"Total markets: {s['total_markets']}, changed: {s['changed_count']}, unchanged: {s['unchanged_count']}", file=sys.stderr)
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
