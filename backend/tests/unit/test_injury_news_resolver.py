"""
Unit tests: injury/news resolver (pure, deterministic).
No DB; uses run_resolver_pure with in-memory claims + policy.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from ingestion.injury_news_resolver import (
    _ClaimRow,
    load_policy,
    run_resolver_pure,
)


def _row(
    claim_id: int,
    team_ref: str = "team_a",
    player_ref: str | None = "p1",
    claim_type: str = "INJURY_STATUS",
    status: str = "OUT",
    confidence: float = 0.9,
    adapter_key: str = "recorded_injury_news_v1",
    recorded_at: datetime | None = None,
    published_at: datetime | None = None,
) -> _ClaimRow:
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts = recorded_at or now
    return _ClaimRow(
        claim_id=claim_id,
        team_ref=team_ref,
        player_ref=player_ref,
        claim_type=claim_type,
        status=status,
        confidence=confidence,
        adapter_key=adapter_key,
        recorded_at=ts,
        published_at=published_at or ts,
    )


def test_resolver_load_policy() -> None:
    """Policy file loads and has expected keys."""
    policy = load_policy("injury_news.v1")
    assert policy.get("policy_version") == "injury_news.v1"
    assert "source_priority" in policy
    assert "conflict_epsilon" in policy
    assert policy.get("conflict_behavior") == "QUESTIONABLE"


def test_resolver_conflict_questionable() -> None:
    """Two claims with different status and scores within conflict_epsilon => QUESTIONABLE, UNRESOLVED_CONFLICT."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy = {
        "policy_version": "injury_news.v1",
        "source_priority": {"src_a": 1.0, "src_b": 1.0},
        "max_age_hours_by_claim_type": {"INJURY_STATUS": 168},
        "recency_half_life_hours": 24,
        "min_confidence_to_consider": 0.5,
        "conflict_epsilon": 0.2,
        "conflict_behavior": "QUESTIONABLE",
    }
    # Same recency/confidence => same score => within epsilon
    rows = [
        _row(1, status="OUT", adapter_key="src_a", confidence=0.9),
        _row(2, status="FIT", adapter_key="src_b", confidence=0.9),
    ]
    resolutions, summary = run_resolver_pure(rows, policy, now)
    assert len(resolutions) == 1
    assert resolutions[0]["resolved_status"] == "QUESTIONABLE"
    assert resolutions[0]["resolution_method"] == "UNRESOLVED_CONFLICT"
    assert summary["conflicts_count"] == 1
    assert set(resolutions[0]["supporting_claim_ids"]) == {"1"}
    assert "2" in resolutions[0]["conflicting_claim_ids"]


def test_resolver_stale_filtered() -> None:
    """Claims older than max_age_hours for their claim_type are dropped."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    old_ts = now - timedelta(hours=200)
    policy = {
        "policy_version": "v1",
        "source_priority": {"a": 1.0},
        "max_age_hours_by_claim_type": {"INJURY_STATUS": 168},
        "recency_half_life_hours": 24,
        "min_confidence_to_consider": 0.5,
        "conflict_epsilon": 0.05,
        "conflict_behavior": "QUESTIONABLE",
    }
    rows = [
        _row(1, status="OUT", recorded_at=old_ts, published_at=old_ts),
    ]
    resolutions, summary = run_resolver_pure(rows, policy, now)
    assert summary["stale_dropped"] == 1
    assert summary["candidate_counts"]["after_filter"] == 0
    assert len(resolutions) == 0


def test_resolver_low_confidence_dropped() -> None:
    """Claims below min_confidence_to_consider are dropped."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy = {
        "policy_version": "v1",
        "source_priority": {"a": 1.0},
        "max_age_hours_by_claim_type": {"INJURY_STATUS": 168},
        "recency_half_life_hours": 24,
        "min_confidence_to_consider": 0.7,
        "conflict_epsilon": 0.05,
        "conflict_behavior": "QUESTIONABLE",
    }
    rows = [
        _row(1, status="OUT", confidence=0.5),
    ]
    resolutions, summary = run_resolver_pure(rows, policy, now)
    assert summary["low_conf_dropped"] == 1
    assert len(resolutions) == 0


def test_resolver_tie_breaker_stable() -> None:
    """Same score/recency: tie-break by claim_id for deterministic ordering."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy = {
        "policy_version": "v1",
        "source_priority": {"a": 1.0},
        "max_age_hours_by_claim_type": {"INJURY_STATUS": 168},
        "recency_half_life_hours": 24,
        "min_confidence_to_consider": 0.5,
        "conflict_epsilon": 0.05,
        "conflict_behavior": "QUESTIONABLE",
    }
    # Two claims same status, same score => tie-break by recorded_at then claim_id (ascending => lower claim_id first, so top = claim_id 1).
    rows = [
        _row(2, status="OUT", confidence=0.9),
        _row(1, status="OUT", confidence=0.9),
    ]
    resolutions, _ = run_resolver_pure(rows, policy, now)
    assert len(resolutions) == 1
    assert resolutions[0]["winning_claim_id"] == "1"  # tie-break: same score, same recorded_at; ascending claim_id => 1 before 2, so top is 1
    assert resolutions[0]["resolved_status"] == "OUT"
    assert resolutions[0]["resolution_method"] == "LATEST_WINS"


def test_resolver_unknown_player_group_key() -> None:
    """Null player_ref grouped as __UNKNOWN_PLAYER__; resolution still deterministic."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy = load_policy("injury_news.v1")
    rows = [
        _row(1, player_ref=None, status="OUT"),
    ]
    resolutions, summary = run_resolver_pure(rows, policy, now)
    assert len(resolutions) == 1
    assert resolutions[0]["team_ref"] == "team_a"
    assert resolutions[0]["player_ref"] is None
    assert resolutions[0]["resolved_status"] == "OUT"


def test_resolver_deterministic_same_input_twice() -> None:
    """Same rows + policy + now => same resolutions and summary (pure)."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy = load_policy("injury_news.v1")
    rows = [
        _row(1, status="OUT"),
        _row(2, team_ref="team_b", status="FIT"),
    ]
    r1, s1 = run_resolver_pure(rows, policy, now)
    r2, s2 = run_resolver_pure(rows, policy, now)
    assert s1 == s2
    assert len(r1) == len(r2)
    for a, b in zip(r1, r2):
        assert a["team_ref"] == b["team_ref"]
        assert a["player_ref"] == b["player_ref"]
        assert a["resolved_status"] == b["resolved_status"]
        assert a["supporting_claim_ids"] == b["supporting_claim_ids"]
        assert a["conflicting_claim_ids"] == b["conflicting_claim_ids"]
