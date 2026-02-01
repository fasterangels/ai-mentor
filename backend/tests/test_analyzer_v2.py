"""Unit tests for Analyzer v2 — gates, markets, determinism.

Run from backend directory: python -m pytest tests/test_analyzer_v2.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend root is on path when running tests (from repo root or backend)
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def test_gates_missing_evidence_triggers_no_prediction():
    """Missing critical evidence (stats) triggers NO_PREDICTION for market."""
    from analyzer.v2.gates import run_hard_gates

    features = {"missing": ["stats"], "domain_quality": {}, "global_flags": []}
    blocked, gate_results, flags = run_hard_gates("RESOLVED", "1X2", features)
    assert blocked is True
    assert "MISSING_KEY_FEATURES" in flags
    gate_ids = [g["gate_id"] for g in gate_results]
    assert "missing_key_features" in gate_ids
    passed = [g for g in gate_results if g["gate_id"] == "missing_key_features"]
    assert len(passed) == 1 and passed[0]["pass"] is False


def test_gates_resolver_not_resolved_blocks():
    """Resolver not RESOLVED => blocked with AMBIGUOUS or NOT_FOUND."""
    from analyzer.v2.gates import run_hard_gates

    features = {"missing": [], "domain_quality": {"stats": {"score": 0.8}}, "global_flags": []}
    blocked_amb, _, flags_amb = run_hard_gates("AMBIGUOUS", "1X2", features)
    assert blocked_amb is True
    assert "AMBIGUOUS" in flags_amb

    blocked_nf, _, flags_nf = run_hard_gates("NOT_FOUND", "1X2", features)
    assert blocked_nf is True
    assert "NOT_FOUND" in flags_nf


def test_gates_unsupported_market_blocks():
    """Unsupported market => blocked with MARKET_NOT_SUPPORTED."""
    from analyzer.v2.gates import run_hard_gates

    features = {"missing": [], "domain_quality": {"stats": {"score": 0.8}}, "global_flags": []}
    blocked, _, flags = run_hard_gates("RESOLVED", "UNKNOWN_MARKET", features)
    assert blocked is True
    assert "MARKET_NOT_SUPPORTED" in flags


def test_market_1x2_returns_valid_contract():
    """1X2 market module returns v2 decision contract (required keys)."""
    from analyzer.v2.markets.market_1x2 import score_1x2

    features = {
        "has_stats": True,
        "team_strength": {
            "home": {"goals_scored": 1.8, "goals_conceded": 1.0},
            "away": {"goals_scored": 1.2, "goals_conceded": 1.4},
        },
        "h2h": {"matches_played": 0},
        "goals_trend": {},
    }
    gate_results = []
    decision = score_1x2(features, gate_results, 0.7, 0.62)
    required = ["market", "decision", "reasons", "flags", "evidence_refs", "policy_version"]
    for k in required:
        assert k in decision, f"missing key {k}"
    assert decision["market"] == "1X2"
    assert decision["decision"] in ("PLAY", "NO_BET", "NO_PREDICTION")
    assert isinstance(decision["reasons"], list)
    assert len(decision["reasons"]) <= 10
    assert isinstance(decision["flags"], list)
    assert isinstance(decision["evidence_refs"], list)


def test_market_ou_25_returns_valid_contract():
    """OU_2.5 market module returns v2 decision contract."""
    from analyzer.v2.markets.market_ou_25 import score_ou_25

    features = {
        "has_stats": True,
        "goals_trend": {
            "home_avg": 1.5,
            "away_avg": 1.2,
            "home_conceded_avg": 1.0,
            "away_conceded_avg": 1.3,
        },
    }
    gate_results = []
    decision = score_ou_25(features, gate_results, 0.7, 0.62)
    assert decision["market"] == "OU_2.5"
    assert decision["decision"] in ("PLAY", "NO_BET", "NO_PREDICTION")
    assert "reasons" in decision and isinstance(decision["reasons"], list)


def test_market_btts_returns_valid_contract():
    """BTTS market module returns v2 decision contract."""
    from analyzer.v2.markets.market_btts import score_btts

    features = {
        "has_stats": True,
        "goals_trend": {
            "home_avg": 1.2,
            "away_avg": 1.0,
            "home_conceded_avg": 1.1,
            "away_conceded_avg": 1.2,
        },
    }
    gate_results = []
    decision = score_btts(features, gate_results, 0.7, 0.62)
    assert decision["market"] == "BTTS"
    assert decision["decision"] in ("PLAY", "NO_BET", "NO_PREDICTION")
    assert "reasons" in decision and isinstance(decision["reasons"], list)


def test_engine_determinism_same_input_same_output():
    """Same input to analyze_v2 yields same output (no randomness)."""
    from analyzer.v2.engine import analyze_v2
    from pipeline.types import DomainData, EvidencePack, QualityReport
    from datetime import datetime, timezone

    # Minimal evidence pack with stats
    now = datetime.now(timezone.utc)
    quality = QualityReport(passed=True, score=0.8, flags=[])
    stats_data = {
        "home_team_stats": {"goals_scored": 1.5, "goals_conceded": 1.0},
        "away_team_stats": {"goals_scored": 1.2, "goals_conceded": 1.2},
        "head_to_head": {"matches_played": 0},
    }
    domains = {
        "stats": DomainData(data=stats_data, quality=quality, sources=[]),
    }
    ep = EvidencePack(match_id="m1", domains=domains, captured_at_utc=now, flags=[])

    out1 = analyze_v2("RESOLVED", ep, ["1X2", "OU_2.5", "BTTS"], 0.62)
    out2 = analyze_v2("RESOLVED", ep, ["1X2", "OU_2.5", "BTTS"], 0.62)
    assert out1["version"] == "v2"
    assert out1["status"] == out2["status"]
    assert out1["decisions"] == out2["decisions"]
    assert out1["analysis_run"]["counts"] == out2["analysis_run"]["counts"]


def test_engine_resolver_not_resolved_returns_no_prediction():
    """When resolver is not RESOLVED, analyzer returns NO_PREDICTION and no market decisions."""
    from analyzer.v2.engine import analyze_v2

    out = analyze_v2("AMBIGUOUS", None, ["1X2"], 0.62)
    assert out["status"] == "NO_PREDICTION"
    assert out["decisions"] == []
    assert out["version"] == "v2"
    assert any(g["gate_id"] == "resolver" and not g["pass"] for g in out["analysis_run"]["gate_results"])


def test_engine_no_crash_on_none_evidence_pack():
    """analyze_v2 does not crash when evidence_pack is None (after RESOLVED)."""
    from analyzer.v2.engine import analyze_v2

    out = analyze_v2("RESOLVED", None, ["1X2", "OU_2.5"], 0.62)
    assert out["version"] == "v2"
    assert out["decisions"]
    # All decisions should be NO_PREDICTION due to missing evidence
    for d in out["decisions"]:
        assert d["decision"] == "NO_PREDICTION"
