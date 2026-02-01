from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

from .policies import (
    CRITICAL_FLAGS,
    EXPECTED_GOALS_THRESHOLD,
    HOME_ADVANTAGE_BASE,
    MIN_EVIDENCE_QUALITY,
    SOFTMAX_TEMPERATURE,
    default_policy,
)
from .types import AnalyzerInput, AnalyzerResult, AnalysisRunMetadata, MarketDecision


def _softmax(scores: Dict[str, float], temperature: float = SOFTMAX_TEMPERATURE) -> Dict[str, float]:
    """Convert scores to probabilities using softmax."""
    if not scores:
        return {}
    
    # Apply temperature scaling
    scaled_scores = {k: v / temperature for k, v in scores.items()}
    
    # Compute exp values
    exp_scores = {k: math.exp(v) for k, v in scaled_scores.items()}
    
    # Normalize
    total = sum(exp_scores.values())
    if total == 0:
        return {k: 1.0 / len(scores) for k in scores}
    
    return {k: v / total for k, v in exp_scores.items()}


def _extract_features(evidence_pack: Any) -> Dict[str, Any]:
    """Extract minimal features from evidence pack."""
    features: Dict[str, Any] = {
        "has_fixtures": False,
        "has_stats": False,
        "home_team": None,
        "away_team": None,
        "is_home": True,  # Default assumption
        "team_strength": {},
        "recent_form": {},
        "h2h": {},
        "goals_trend": {},
    }
    
    # Extract fixtures data
    fixtures_domain = evidence_pack.domains.get("fixtures")
    if fixtures_domain and fixtures_domain.data:
        features["has_fixtures"] = True
        fixtures_data = fixtures_domain.data
        features["home_team"] = fixtures_data.get("home_team")
        features["away_team"] = fixtures_data.get("away_team")
        features["is_home"] = True  # Always home team perspective
    
    # Extract stats data
    stats_domain = evidence_pack.domains.get("stats")
    if stats_domain and stats_domain.data:
        features["has_stats"] = True
        stats_data = stats_domain.data
        
        # Extract team strength proxies
        home_stats = stats_data.get("home_team_stats", {})
        away_stats = stats_data.get("away_team_stats", {})
        
        features["team_strength"] = {
            "home": {
                "goals_scored": home_stats.get("goals_scored", 0.0),
                "goals_conceded": home_stats.get("goals_conceded", 0.0),
                "shots_per_game": home_stats.get("shots_per_game", 0.0),
                "possession_avg": home_stats.get("possession_avg", 0.0),
            },
            "away": {
                "goals_scored": away_stats.get("goals_scored", 0.0),
                "goals_conceded": away_stats.get("goals_conceded", 0.0),
                "shots_per_game": away_stats.get("shots_per_game", 0.0),
                "possession_avg": away_stats.get("possession_avg", 0.0),
            },
        }
        
        # Extract H2H
        h2h = stats_data.get("head_to_head", {})
        features["h2h"] = {
            "matches_played": h2h.get("matches_played", 0),
            "home_wins": h2h.get("home_wins", 0),
            "away_wins": h2h.get("away_wins", 0),
            "draws": h2h.get("draws", 0),
        }
        
        # Goals trend (simplified from stats)
        features["goals_trend"] = {
            "home_avg": home_stats.get("goals_scored", 0.0),
            "away_avg": away_stats.get("goals_scored", 0.0),
            "home_conceded_avg": home_stats.get("goals_conceded", 0.0),
            "away_conceded_avg": away_stats.get("goals_conceded", 0.0),
        }
    
    return features


def _check_preconditions(evidence_pack: Any, policy: Any) -> Tuple[bool, List[str]]:
    """Check if analysis can proceed."""
    flags = []
    
    # Check for critical flags
    for flag in evidence_pack.flags:
        if flag in CRITICAL_FLAGS:
            flags.append(flag)
            return False, flags
    
    # Check evidence quality
    min_quality = MIN_EVIDENCE_QUALITY
    for domain_name, domain_data in evidence_pack.domains.items():
        if domain_data.quality.score < min_quality:
            flags.append(f"LOW_QUALITY_{domain_name.upper()}")
    
    # If critical flags present, return NO_PREDICTION
    if flags:
        return False, flags
    
    return True, []


def _analyze_1x2(features: Dict[str, Any], policy: Any) -> MarketDecision:
    """Analyze 1X2 market deterministically."""
    decision = MarketDecision(market="1X2", decision="NO_BET")
    reasons: List[str] = []
    
    # Check required features
    if not features.get("has_stats"):
        reasons.append("INSUFFICIENT_DATA_FOR_MARKET")
        decision.reasons = reasons
        return decision
    
    team_strength = features.get("team_strength", {})
    if not team_strength.get("home") or not team_strength.get("away"):
        reasons.append("INSUFFICIENT_DATA_FOR_MARKET")
        decision.reasons = reasons
        return decision
    
    home_strength = team_strength["home"]
    away_strength = team_strength["away"]
    
    # Compute base scores
    # Home advantage
    home_advantage = HOME_ADVANTAGE_BASE
    
    # Relative team strength (normalized attack - defense)
    home_attack = home_strength.get("goals_scored", 0.0)
    home_defense = home_strength.get("goals_conceded", 0.0)
    away_attack = away_strength.get("goals_scored", 0.0)
    away_defense = away_strength.get("goals_conceded", 0.0)
    
    home_net = home_attack - away_defense
    away_net = away_attack - home_defense
    
    # H2H adjustment (if available)
    h2h = features.get("h2h", {})
    h2h_weight = 0.1
    if h2h.get("matches_played", 0) > 0:
        total = h2h["matches_played"]
        home_h2h_score = (h2h.get("home_wins", 0) * 1.0 + h2h.get("draws", 0) * 0.5) / total
        away_h2h_score = (h2h.get("away_wins", 0) * 1.0 + h2h.get("draws", 0) * 0.5) / total
        home_net += (home_h2h_score - 0.5) * h2h_weight
        away_net += (away_h2h_score - 0.5) * h2h_weight
        reasons.append("H2H_DATA_USED")
    
    # Compute raw scores
    scores = {
        "HOME": home_net + home_advantage,
        "DRAW": 0.0,  # Draw is neutral baseline
        "AWAY": away_net - home_advantage,
    }
    
    # Convert to probabilities
    probabilities = _softmax(scores)
    decision.probabilities = probabilities
    
    # Compute separation
    sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_probs) >= 2:
        top_prob = sorted_probs[0][1]
        second_prob = sorted_probs[1][1]
        separation = top_prob - second_prob
        decision.separation = separation
        
        # Decision rules
        if separation < policy.min_sep_1x2:
            decision.decision = "NO_BET"
            reasons.append(f"SEPARATION_BELOW_THRESHOLD_{separation:.3f}")
        else:
            decision.decision = sorted_probs[0][0]
            reasons.append(f"TOP_OUTCOME_{sorted_probs[0][0]}")
            if home_advantage > 0:
                reasons.append("HOME_ADVANTAGE_PRESENT")
    else:
        decision.separation = 0.0
        reasons.append("INSUFFICIENT_DATA_FOR_MARKET")
    
    decision.reasons = reasons
    return decision


def _analyze_ou25(features: Dict[str, Any], policy: Any) -> MarketDecision:
    """Analyze Over/Under 2.5 goals market deterministically."""
    decision = MarketDecision(market="OU25", decision="NO_BET")
    reasons: List[str] = []
    
    # Check required features
    if not features.get("has_stats"):
        reasons.append("INSUFFICIENT_DATA_FOR_MARKET")
        decision.reasons = reasons
        return decision
    
    goals_trend = features.get("goals_trend", {})
    if not goals_trend:
        reasons.append("INSUFFICIENT_DATA_FOR_MARKET")
        decision.reasons = reasons
        return decision
    
    # Estimate expected goals proxy
    home_goals_avg = goals_trend.get("home_avg", 0.0)
    away_goals_avg = goals_trend.get("away_avg", 0.0)
    home_conceded_avg = goals_trend.get("home_conceded_avg", 0.0)
    away_conceded_avg = goals_trend.get("away_conceded_avg", 0.0)
    
    # Expected goals = (home attack + away defense) / 2 + (away attack + home defense) / 2
    expected_goals = (home_goals_avg + away_conceded_avg) / 2.0 + (away_goals_avg + home_conceded_avg) / 2.0
    
    # Map expected goals to probabilities using fixed curve
    # Simple sigmoid-like mapping around threshold 2.5
    if expected_goals <= 0:
        p_over = 0.0
    else:
        # Deterministic curve: P(OVER) increases with expected_goals
        # Using tanh-based mapping centered at 2.5
        diff = expected_goals - EXPECTED_GOALS_THRESHOLD
        p_over = 0.5 + 0.5 * math.tanh(diff * 0.5)  # Scale factor 0.5 for smoothness
    
    p_under = 1.0 - p_over
    
    probabilities = {"OVER": p_over, "UNDER": p_under}
    decision.probabilities = probabilities
    
    # Compute separation
    separation = abs(p_over - p_under)
    decision.separation = separation
    
    # Decision rules
    if separation < policy.min_sep_ou:
        decision.decision = "NO_BET"
        reasons.append(f"SEPARATION_BELOW_THRESHOLD_{separation:.3f}")
    else:
        if p_over > p_under:
            decision.decision = "OVER"
            reasons.append("EXPECTED_GOALS_ABOVE_THRESHOLD")
        else:
            decision.decision = "UNDER"
            reasons.append("EXPECTED_GOALS_BELOW_THRESHOLD")
    
    if expected_goals < 1.5:
        reasons.append("LOW_GOALS_TREND")
    elif expected_goals > 3.5:
        reasons.append("HIGH_GOALS_TREND")
    
    decision.reasons = reasons
    return decision


def _analyze_ggng(features: Dict[str, Any], policy: Any) -> MarketDecision:
    """Analyze Both Teams to Score (GG/NG) market deterministically."""
    decision = MarketDecision(market="GGNG", decision="NO_BET")
    reasons: List[str] = []
    
    # Check required features
    if not features.get("has_stats"):
        reasons.append("INSUFFICIENT_DATA_FOR_MARKET")
        decision.reasons = reasons
        return decision
    
    goals_trend = features.get("goals_trend", {})
    if not goals_trend:
        reasons.append("INSUFFICIENT_DATA_FOR_MARKET")
        decision.reasons = reasons
        return decision
    
    # Estimate both-teams-to-score likelihood
    home_goals_avg = goals_trend.get("home_avg", 0.0)
    away_goals_avg = goals_trend.get("away_avg", 0.0)
    home_conceded_avg = goals_trend.get("home_conceded_avg", 0.0)
    away_conceded_avg = goals_trend.get("away_conceded_avg", 0.0)
    
    # P(GG) = P(home scores) * P(away scores)
    # P(home scores) ~ home attack strength vs away defense
    # P(away scores) ~ away attack strength vs home defense
    
    # Scoring frequency proxies
    home_scoring_prob = min(1.0, max(0.0, (home_goals_avg / 3.0)))  # Normalize to 0-1
    away_scoring_prob = min(1.0, max(0.0, (away_goals_avg / 3.0)))
    
    # Conceded frequency proxies (inverse defense strength)
    home_conceding_prob = min(1.0, max(0.0, (home_conceded_avg / 3.0)))
    away_conceding_prob = min(1.0, max(0.0, (away_conceded_avg / 3.0)))
    
    # Combined: P(home scores) = home attack * away defense weakness
    p_home_scores = home_scoring_prob * away_conceding_prob
    p_away_scores = away_scoring_prob * home_conceding_prob
    
    # P(GG) = P(home scores) * P(away scores)
    p_gg = p_home_scores * p_away_scores
    p_ng = 1.0 - p_gg
    
    probabilities = {"GG": p_gg, "NG": p_ng}
    decision.probabilities = probabilities
    
    # Compute separation
    separation = abs(p_gg - p_ng)
    decision.separation = separation
    
    # Decision rules
    if separation < policy.min_sep_gg:
        decision.decision = "NO_BET"
        reasons.append(f"SEPARATION_BELOW_THRESHOLD_{separation:.3f}")
    else:
        if p_gg > p_ng:
            decision.decision = "GG"
            reasons.append("BOTH_TEAMS_SCORING_TREND")
        else:
            decision.decision = "NG"
            reasons.append("DEFENSIVE_STRENGTH_PRESENT")
    
    decision.reasons = reasons
    return decision


def _compute_confidence_and_risk(
    decision: MarketDecision,
    evidence_quality_score: float,
    policy: Any,
) -> None:
    """Compute confidence and risk for a decision."""
    # Confidence derived from separation and evidence quality
    separation_component = min(1.0, decision.separation * 2.0)  # Scale separation to 0-1
    quality_component = evidence_quality_score
    
    # Weighted combination
    confidence = 0.6 * separation_component + 0.4 * quality_component
    
    # Risk = 1 - confidence, capped by policy
    risk = 1.0 - confidence
    risk_cap = policy.risk_caps.get("default", 0.35)
    risk = min(risk, risk_cap)
    
    decision.confidence = confidence
    decision.risk = risk
    
    # Force NO_BET if confidence below minimum
    if confidence < policy.min_confidence and decision.decision != "NO_BET":
        decision.decision = "NO_BET"
        decision.reasons.append(f"CONFIDENCE_BELOW_THRESHOLD_{confidence:.3f}")


def analyze(input_data: AnalyzerInput) -> AnalyzerResult:
    """Run analyzer v1 on evidence pack.

    Deterministic: same input → same output.
    Returns NO_PREDICTION if preconditions fail.
    Returns NO_BET for markets that don't meet thresholds.
    """
    # Use default policy if not provided
    policy = input_data.policy if input_data.policy else default_policy
    
    # Early exit if no evidence pack
    if input_data.evidence_pack is None:
        return AnalyzerResult(
            status="NO_PREDICTION",
            analysis_run=AnalysisRunMetadata(
                logic_version="analyzer_v1",
                flags=["NO_EVIDENCE_PACK"],
            ),
            decisions=[],
        )
    
    # Check preconditions
    can_proceed, flags = _check_preconditions(input_data.evidence_pack, policy)
    if not can_proceed:
        return AnalyzerResult(
            status="NO_PREDICTION",
            analysis_run=AnalysisRunMetadata(
                logic_version="analyzer_v1",
                flags=flags,
            ),
            decisions=[],
        )
    
    # Extract features
    features = _extract_features(input_data.evidence_pack)
    
    # Compute overall evidence quality score
    quality_scores = [
        domain_data.quality.score
        for domain_data in input_data.evidence_pack.domains.values()
    ]
    evidence_quality_score = (
        sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    )
    
    # Analyze each market independently
    decisions: List[MarketDecision] = []
    
    for market in input_data.markets:
        if market == "1X2":
            decision = _analyze_1x2(features, policy)
        elif market == "OU25":
            decision = _analyze_ou25(features, policy)
        elif market == "GGNG":
            decision = _analyze_ggng(features, policy)
        else:
            # Unknown market
            decision = MarketDecision(
                market=market,
                decision="NO_BET",
                reasons=["UNKNOWN_MARKET"],
            )
        
        # Compute confidence and risk
        _compute_confidence_and_risk(decision, evidence_quality_score, policy)
        
        decisions.append(decision)
    
    # Collect flags from decisions
    all_flags = flags.copy()
    for decision in decisions:
        if decision.decision == "NO_BET":
            all_flags.append(f"NO_BET_{decision.market}")
    
    return AnalyzerResult(
        status="OK",
        analysis_run=AnalysisRunMetadata(
            logic_version="analyzer_v1",
            flags=all_flags,
        ),
        decisions=decisions,
    )
