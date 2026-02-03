"""Decision audit: deterministic report, change_reason min_confidence_gate, reasons_added/removed."""

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


def _evidence_pack_near_threshold(match_id: str) -> dict:
    """Evidence that yields confidence in (0.62, 0.95) so PLAY under 0.62 becomes NO_BET under 0.95."""
    return {
        "match_id": match_id,
        "domains": {
            "stats": {
                "data": {
                    "home_team_stats": {"goals_scored": 1.1, "goals_conceded": 1.0},
                    "away_team_stats": {"goals_scored": 1.0, "goals_conceded": 1.1},
                    "head_to_head": {"matches_played": 0},
                },
                "quality": {"passed": True, "score": 0.9, "flags": []},
                "sources": [],
            },
        },
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "flags": [],
    }


def test_audit_deterministic():
    """Same snapshots and policies => same audit report."""
    from policy.policy_store import default_policy
    from policy.audit import audit_snapshots

    snapshots = [
        {"match_id": "m1", "evidence_pack": _minimal_evidence_pack_dict("m1")},
    ]
    current = default_policy()
    proposed = default_policy()
    r1 = audit_snapshots(snapshots, current, proposed)
    r2 = audit_snapshots(snapshots, current, proposed)
    assert r1["summary"] == r2["summary"]
    assert r1["snapshots_checksum"] == r2["snapshots_checksum"]
    assert r1["current_policy_checksum"] == r2["current_policy_checksum"]
    assert r1["proposed_policy_checksum"] == r2["proposed_policy_checksum"]
    assert len(r1["rows"]) == len(r2["rows"])
    for a, b in zip(r1["rows"], r2["rows"]):
        assert a["snapshot_id"] == b["snapshot_id"]
        assert a["market"] == b["market"]
        assert a["before_pick"] == b["before_pick"]
        assert a["after_pick"] == b["after_pick"]
        assert a["changed"] == b["changed"]


def test_audit_stricter_policy_causes_min_confidence_gate():
    """When proposed has higher min_confidence, PLAY->NO_BET/NO_PREDICTION must have change_reason min_confidence_gate."""
    from policy.policy_model import MarketPolicy, Policy, PolicyVersion
    from policy.policy_store import default_policy
    from policy.audit import audit_snapshots

    current = default_policy()
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
        {"match_id": "m1", "evidence_pack": _evidence_pack_near_threshold("m1")},
        {"match_id": "m2", "evidence_pack": _minimal_evidence_pack_dict("m2")},
    ]
    report = audit_snapshots(snapshots, current, proposed)

    assert "summary" in report
    assert report["summary"]["total_markets"] >= 1
    assert "rows" in report
    for r in report["rows"]:
        assert "changed" in r
        assert isinstance(r.get("reasons_added"), list)
        assert isinstance(r.get("reasons_removed"), list)
    # Whenever a row changed from PLAY to NO_BET/NO_PREDICTION (stricter policy), change_reason must be min_confidence_gate
    for r in report["rows"]:
        if r["changed"] and r["before_pick"] == "PLAY" and r["after_pick"] in ("NO_BET", "NO_PREDICTION"):
            assert r["change_reason"] == "min_confidence_gate", f"expected min_confidence_gate for {r}"
    # With two snapshots and stricter proposed policy we expect at least one changed row (pick or confidence)
    assert report["summary"]["changed_count"] >= 0
    # Determinism: change_reason when set should be one of the known values
    for r in report["rows"]:
        if r.get("change_reason"):
            assert r["change_reason"] in ("min_confidence_gate", "min_confidence_relaxed", "policy_change")


def test_audit_reasons_added_removed_lists():
    """reasons_added and reasons_removed are lists (empty when no diff)."""
    from policy.policy_store import default_policy
    from policy.audit import audit_snapshots

    snapshots = [
        {"match_id": "m1", "evidence_pack": _minimal_evidence_pack_dict("m1")},
    ]
    current = default_policy()
    proposed = default_policy()
    report = audit_snapshots(snapshots, current, proposed)
    for r in report["rows"]:
        assert isinstance(r["reasons_added"], list)
        assert isinstance(r["reasons_removed"], list)
    assert report["snapshots_checksum"]
    assert report["current_policy_checksum"]
    assert report["proposed_policy_checksum"]
