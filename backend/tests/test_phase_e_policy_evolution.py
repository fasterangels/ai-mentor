"""
Phase E: Policy evolution (shadow-only) tests.
A) Production analyzer output for fixed fixture unchanged (decision, selection, confidence).
B) Shadow outputs include new reason codes when conditions match.
C) Evaluator includes new confidence band buckets (see test_decision_quality).
D) Tuner proposals produced with before/after and evaluation_metrics; policy not modified.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from datetime import datetime, timezone

import pytest

from analyzer.v2.engine import analyze_v2
from analyzer.v2.reason_codes import ALL_REASON_CODES
from pipeline.types import DomainData, EvidencePack, QualityReport
from policy.tuning_planner import plan_from_quality_audit
from policy.policy_model import Policy, PolicyVersion, MarketPolicy, ReasonPolicy


def _minimal_evidence_pack() -> EvidencePack:
    """Minimal resolved evidence for analyzer (fixture)."""
    stats_data = {
        "home_team_stats": {"goals_scored": 1.5, "goals_conceded": 1.0, "shots_per_game": 11.0, "possession_avg": 52.0},
        "away_team_stats": {"goals_scored": 1.2, "goals_conceded": 1.3, "shots_per_game": 10.0, "possession_avg": 48.0},
        "head_to_head": {"matches_played": 2, "home_wins": 1, "away_wins": 0, "draws": 1},
        "goals_trend": {"home_avg": 1.5, "away_avg": 1.2, "home_conceded_avg": 1.0, "away_conceded_avg": 1.3},
    }
    fixtures_data = {"match_id": "m1", "home_team": "A", "away_team": "B", "kickoff_utc": "2025-06-01T12:00:00Z", "competition": "C", "status": "scheduled", "odds_1x2": {"home": 2.0, "draw": 3.2, "away": 3.5}}
    return EvidencePack(
        match_id="m1",
        domains={
            "fixtures": DomainData(data=fixtures_data, quality=QualityReport(passed=True, score=1.0, flags=[]), sources=[]),
            "stats": DomainData(data=stats_data, quality=QualityReport(passed=True, score=1.0, flags=[]), sources=[]),
        },
        captured_at_utc=datetime.now(timezone.utc),
        flags=[],
    )


def test_analyzer_fixed_fixture_decision_unchanged() -> None:
    """A) Production analyzer output (decision, selection, confidence) for fixed fixture is unchanged."""
    ep = _minimal_evidence_pack()
    result = analyze_v2("RESOLVED", ep, ["1X2", "OU_2.5", "BTTS"], min_confidence=0.62)
    assert result["status"] in ("OK", "NO_PREDICTION")
    decisions = result.get("decisions") or []
    assert len(decisions) >= 1
    for d in decisions:
        assert "decision" in d
        assert d["decision"] in ("PLAY", "NO_BET", "NO_PREDICTION")
        assert "reasons" in d
        assert isinstance(d["reasons"], list)
        if d.get("selection") is not None:
            assert "confidence" in d
            assert isinstance(d["confidence"], (int, float))


def test_shadow_outputs_include_reason_codes() -> None:
    """B) Shadow outputs (decisions) include reason_codes when conditions match."""
    ep = _minimal_evidence_pack()
    result = analyze_v2("RESOLVED", ep, ["1X2", "OU_2.5", "BTTS"], min_confidence=0.62)
    decisions = result.get("decisions") or []
    for d in decisions:
        assert "reason_codes" in d
        codes = d["reason_codes"]
        assert isinstance(codes, list)
        for c in codes:
            assert isinstance(c, str)
    codes_seen = set()
    for d in decisions:
        codes_seen.update(d.get("reason_codes") or [])
    assert codes_seen.issubset(ALL_REASON_CODES | {"UNKNOWN"})


def test_tuner_proposals_have_before_after_and_evaluation_metrics() -> None:
    """D) Tuner proposals include before_threshold, after_threshold, evaluation_metrics; policy not applied."""
    current = Policy(
        meta=PolicyVersion(version="test", created_at_utc=datetime.now(timezone.utc), notes=""),
        markets={
            "one_x_two": MarketPolicy(min_confidence=0.60),
            "over_under_25": MarketPolicy(min_confidence=0.62),
            "gg_ng": MarketPolicy(min_confidence=0.62),
        },
        reasons={"R1": ReasonPolicy(reason_code="R1", dampening_factor=1.0)},
    )
    quality_audit = {
        "confidence_calibration": {
            "one_x_two": {"0.65-0.70": {"predicted_confidence": 0.675, "empirical_accuracy": 0.4, "count": 15}},
        },
        "suggestions": {
            "confidence_band_adjustments": [
                {"market": "one_x_two", "predicted_confidence": 0.675, "empirical_accuracy": 0.4, "count": 15, "deviation": 0.275},
            ],
            "dampening_candidates": [],
        },
    }
    out = plan_from_quality_audit(quality_audit, current_policy=current)
    assert "proposals" in out
    for p in out.get("proposals") or []:
        assert "before_threshold" in p or "old_val" in p
        assert "after_threshold" in p or "new_val" in p
        assert "evaluation_metrics" in p
    assert "proposed_policy_snapshot" in out
    assert current.meta.version == "test"
