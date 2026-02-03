"""GET /api/v1/policy/active and POST /api/v1/policy/tune/shadow (read-only; no apply)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from policy.policy_runtime import get_active_policy
from policy.policy_store import default_policy_path
from policy.tuner import run_tuner, PolicyProposal
from policy.replay import run_replay

router = APIRouter(prefix="/policy", tags=["policy"])


@router.get("/active")
async def get_active() -> dict:
    """Return active policy meta + thresholds (no secrets). Read-only."""
    policy = get_active_policy()
    return {
        "meta": {
            "version": policy.meta.version,
            "created_at_utc": policy.meta.created_at_utc.isoformat(),
            "notes": policy.meta.notes,
        },
        "markets": {
            k: {"min_confidence": v.min_confidence}
            for k, v in policy.markets.items()
        },
        "reasons": {
            k: {"dampening_factor": v.dampening_factor}
            for k, v in policy.reasons.items()
        },
    }


@router.post("/tune/shadow")
async def tune_shadow(body: dict | None = None) -> dict:
    """
    Run tuner on evaluation report (from body or latest file); return proposal + replay_report.
    Does NOT apply policy. No activate endpoint.
    """
    body = body or {}
    evaluation_report = body.get("evaluation_report")
    if evaluation_report is None:
        # Try default path
        default_path = Path("evaluation_report.json")
        if not default_path.is_file():
            default_path = Path(__file__).resolve().parent.parent.parent.parent / "evaluation_report.json"
        if default_path.is_file():
            import json
            with open(default_path, encoding="utf-8") as f:
                evaluation_report = json.load(f)
        else:
            raise HTTPException(status_code=400, detail="evaluation_report not in body and evaluation_report.json not found")
    if not isinstance(evaluation_report, dict):
        raise HTTPException(status_code=400, detail="evaluation_report must be a dict")

    proposal: PolicyProposal = run_tuner(evaluation_report)

    # Optional replay if snapshots provided
    snapshots = body.get("snapshots")
    if isinstance(snapshots, list) and len(snapshots) > 0:
        current = get_active_policy()
        replay_report = run_replay(snapshots, current, proposal.proposed_policy)
    else:
        replay_report = None

    # Serialize proposal for response
    def _serialize_proposal(p: PolicyProposal) -> dict[str, Any]:
        return {
            "proposed_policy": p.proposed_policy.model_dump(mode="json"),
            "diffs": [list(d) for d in p.diffs],
            "guardrails_results": [list(g) for g in p.guardrails_results],
            "evaluation_report_checksum": p.evaluation_report_checksum,
        }

    return {
        "proposal": _serialize_proposal(proposal),
        "replay_report": replay_report,
    }
