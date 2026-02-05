#!/usr/bin/env python3
"""
Replay regression harness: run analyzer with current vs proposed policy on stored snapshots;
compare predictions and confidence; write replay_report.json with PASS/FAIL.

Usage:
  python tools/replay_regression.py --snapshots path/to/snapshots.json --proposal path/to/proposal.json [--output replay_report.json]
  Snapshots JSON: list of { "match_id": "...", "evidence_pack": { ... } } (evidence_pack as dict).
  Proposal JSON: { "proposed_policy": { ... } } or full PolicyProposal from tuner.
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
from policy.replay import run_replay


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
    ap = argparse.ArgumentParser(description="Replay regression: current vs proposed policy on snapshots")
    ap.add_argument("--snapshots", type=Path, required=True, help="JSON: list of { match_id, evidence_pack }")
    ap.add_argument("--proposal", type=Path, required=True, help="JSON: proposal with proposed_policy or Policy")
    ap.add_argument("--output", type=Path, default=Path("replay_report.json"), help="Output report path")
    args = ap.parse_args()

    snapshots = load_snapshots(args.snapshots)
    proposed_policy = load_proposed_policy(args.proposal)
    current_policy = get_active_policy()

    report = run_replay(snapshots, current_policy, proposed_policy)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Replay result: {report['replay_result']}", file=sys.stderr)
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0 if report["replay_result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
