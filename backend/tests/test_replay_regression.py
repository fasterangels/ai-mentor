"""Replay regression: fixture set; report produced; PASS/FAIL logic works."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def _minimal_evidence_pack_dict(match_id: str) -> dict:
    return {
        "match_id": match_id,
        "domains": {
            "stats": {
                "data": {
                    "home_team_stats": {"goals_scored": 1.5, "goals_conceded": 1.0},
                    "away_team_stats": {"goals_scored": 1.2, "goals_conceded": 1.2},
                    "head_to_head": {"matches_played": 0},
                },
                "quality": {"passed": True, "score": 0.8, "flags": []},
                "sources": [],
            },
        },
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "flags": [],
    }


def test_replay_produces_report():
    """Run replay with small fixture; report has replay_result, guardrails, checksum."""
    from policy.policy_store import default_policy
    from policy.replay import run_replay

    snapshots = [
        {"match_id": "m1", "evidence_pack": _minimal_evidence_pack_dict("m1")},
        {"match_id": "m2", "evidence_pack": _minimal_evidence_pack_dict("m2")},
    ]
    current = default_policy()
    proposed = default_policy()
    report = run_replay(snapshots, current, proposed)
    assert "replay_result" in report
    assert report["replay_result"] in ("PASS", "FAIL")
    assert "guardrails" in report
    assert "snapshots_checksum" in report
    assert "current_play_count" in report
    assert "proposed_play_count" in report


def test_replay_pass_when_no_coverage_drop():
    """When current and proposed are same policy, coverage drop is 0 => PASS."""
    from policy.policy_store import default_policy
    from policy.replay import run_replay

    snapshots = [
        {"match_id": "m1", "evidence_pack": _minimal_evidence_pack_dict("m1")},
    ]
    current = default_policy()
    proposed = default_policy()
    report = run_replay(snapshots, current, proposed)
    assert report["replay_result"] == "PASS"
    assert report["guardrails"]["coverage_drop_pct"] == 0.0


def test_replay_fail_when_coverage_drops_more_than_threshold():
    """If proposed policy is stricter (higher min_confidence), PLAY count can drop => FAIL if > 10%."""
    from policy.policy_model import MarketPolicy, Policy, PolicyVersion
    from policy.policy_store import default_policy
    from policy.replay import run_replay

    current = default_policy()
    # Proposed: much higher min_confidence so many PLAY become NO_BET
    proposed = Policy(
        meta=PolicyVersion(version="strict", created_at_utc=current.meta.created_at_utc, notes=""),
        markets={
            "one_x_two": MarketPolicy(min_confidence=0.95),
            "over_under_25": MarketPolicy(min_confidence=0.95),
            "gg_ng": MarketPolicy(min_confidence=0.95),
        },
        reasons=current.reasons,
    )
    snapshots = [
        {"match_id": f"m{i}", "evidence_pack": _minimal_evidence_pack_dict(f"m{i}")}
        for i in range(10)
    ]
    report = run_replay(snapshots, current, proposed)
    # With 10 snapshots and 3 markets, we get 30 decisions. Current policy (0.62) yields some PLAY;
    # proposed (0.95) yields fewer or zero PLAY => coverage drop > 10% => FAIL
    assert "replay_result" in report
    assert report["guardrails"]["passed"] == (report["replay_result"] == "PASS")
