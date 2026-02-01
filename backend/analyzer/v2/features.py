"""Analyzer v2 — Deterministic feature extraction from evidence_pack.

Conservative: pull only explicitly available fields. Mark missing; gates handle.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pipeline.types import DomainData, EvidencePack


def extract_features(evidence_pack: Optional[EvidencePack]) -> Dict[str, Any]:
    """
    Extract features from evidence_pack. No guessing; missing critical
    features are recorded in "missing" and quality/flags preserved.
    """
    features: Dict[str, Any] = {
        "has_fixtures": False,
        "has_stats": False,
        "home_team": None,
        "away_team": None,
        "team_strength": {},
        "h2h": {},
        "goals_trend": {},
        "missing": [],
        "domain_quality": {},
        "global_flags": [],
    }

    if evidence_pack is None:
        features["missing"] = ["evidence_pack"]
        return features

    features["global_flags"] = list(getattr(evidence_pack, "flags", []) or [])

    domains = getattr(evidence_pack, "domains", {}) or {}
    for domain_name, domain_data in domains.items():
        if not isinstance(domain_data, DomainData):
            continue
        features["domain_quality"][domain_name] = {
            "score": domain_data.quality.score,
            "passed": domain_data.quality.passed,
            "flags": list(domain_data.quality.flags or []),
        }

    # Fixtures
    fixtures = domains.get("fixtures")
    if fixtures and getattr(fixtures, "data", None):
        data = fixtures.data
        features["has_fixtures"] = True
        features["home_team"] = data.get("home_team")
        features["away_team"] = data.get("away_team")
    else:
        features["missing"].append("fixtures")

    # Stats (team strength, H2H, goals trend)
    stats = domains.get("stats")
    if stats and getattr(stats, "data", None):
        data = stats.data
        features["has_stats"] = True
        home_stats = data.get("home_team_stats") or {}
        away_stats = data.get("away_team_stats") or {}
        features["team_strength"] = {
            "home": {
                "goals_scored": _float(home_stats.get("goals_scored")),
                "goals_conceded": _float(home_stats.get("goals_conceded")),
                "shots_per_game": _float(home_stats.get("shots_per_game")),
                "possession_avg": _float(home_stats.get("possession_avg")),
            },
            "away": {
                "goals_scored": _float(away_stats.get("goals_scored")),
                "goals_conceded": _float(away_stats.get("goals_conceded")),
                "shots_per_game": _float(away_stats.get("shots_per_game")),
                "possession_avg": _float(away_stats.get("possession_avg")),
            },
        }
        h2h = data.get("head_to_head") or {}
        features["h2h"] = {
            "matches_played": _int(h2h.get("matches_played")),
            "home_wins": _int(h2h.get("home_wins")),
            "away_wins": _int(h2h.get("away_wins")),
            "draws": _int(h2h.get("draws")),
        }
        features["goals_trend"] = {
            "home_avg": _float(home_stats.get("goals_scored")),
            "away_avg": _float(away_stats.get("goals_scored")),
            "home_conceded_avg": _float(home_stats.get("goals_conceded")),
            "away_conceded_avg": _float(away_stats.get("goals_conceded")),
        }
    else:
        features["missing"].append("stats")

    return features


def _float(x: Any) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _int(x: Any) -> int:
    if x is None:
        return 0
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def evidence_quality_score(features: Dict[str, Any]) -> float:
    """Overall evidence quality 0..1 from domain_quality scores."""
    dq = features.get("domain_quality") or {}
    if not dq:
        return 0.0
    scores = [v.get("score", 0.0) for v in dq.values() if isinstance(v, dict)]
    return sum(scores) / len(scores) if scores else 0.0


def consensus_quality_from_features(features: Dict[str, Any]) -> float:
    """
    Consensus/agreement score 0..1 from evidence. If pipeline does not
    expose it, derive conservatively from domain quality and flags.
    """
    dq = features.get("domain_quality") or {}
    if not dq:
        return 0.0
    # Use minimum domain score as conservative consensus proxy
    scores = [v.get("score", 0.0) for v in dq.values() if isinstance(v, dict)]
    if not scores:
        return 0.0
    # Penalize if LOW_AGREEMENT or similar in flags
    flags = features.get("global_flags") or []
    for f in flags:
        if "LOW_AGREEMENT" in str(f).upper() or "CONFLICT" in str(f).upper():
            return min(scores) * 0.7
    return min(scores)
