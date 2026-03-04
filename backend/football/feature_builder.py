from __future__ import annotations

from typing import Any

from .models import FootballFeatures, asdict_deep
from .providers import FootballOddsProvider, FootballStatsProvider
from .injury_impact import build_injury_impact
from .lineup_strength import build_lineup_strength
from .market_movement import update_and_analyze
from .odds_intelligence import build_odds_intelligence
from .prediction_model import build_prediction
from .schedule_fatigue import build_schedule_fatigue
from .tactical_signals import build_tactical_signals
from .team_intelligence import build_team_intelligence


def build_features(
    match_id: str,
    stats: FootballStatsProvider,
    odds: FootballOddsProvider,
    *,
    last_n: int = 6,
    h2h_n: int = 6,
) -> FootballFeatures:
    """
    Build football features for a single match using the given providers.
    """
    match = stats.get_match(match_id)
    lineups = stats.get_lineups(match_id)
    injuries = stats.get_injuries(match_id)

    home_last = stats.get_last_matches(match.home.team_id, n=last_n)
    away_last = stats.get_last_matches(match.away.team_id, n=last_n)
    last6 = {
        match.home.team_id: home_last[:last_n],
        match.away.team_id: away_last[:last_n],
    }

    home_team_id = match.home.team_id
    away_team_id = match.away.team_id
    home_lineup = build_lineup_strength(home_team_id, lineups, injuries)
    away_lineup = build_lineup_strength(away_team_id, lineups, injuries)
    home_injury = build_injury_impact(home_team_id, injuries)
    away_injury = build_injury_impact(away_team_id, injuries)
    home_intel = build_team_intelligence(home_team_id, last6.get(home_team_id, []))
    away_intel = build_team_intelligence(away_team_id, last6.get(away_team_id, []))

    h2h = stats.get_h2h(match.home.team_id, match.away.team_id, n=h2h_n)
    last_home = last6.get(home_team_id, [])
    last_away = last6.get(away_team_id, [])
    home_fatigue = build_schedule_fatigue(home_team_id, last_home)
    away_fatigue = build_schedule_fatigue(away_team_id, last_away)
    tactical = build_tactical_signals(last_home, last_away, h2h)

    odds_quotes = odds.get_odds(match_id)
    odds_intel = build_odds_intelligence(odds_quotes)
    movement = update_and_analyze(match_id, odds_quotes)

    meta = {
        "stats_provider": getattr(stats, "name", type(stats).__name__),
        "odds_provider": getattr(odds, "name", type(odds).__name__),
        "lineup_count": len(lineups),
        "injury_count": len(injuries),
        "last_n": last_n,
        "h2h_n": h2h_n,
        "h2h_count": len(h2h),
        "odds_count": len(odds_quotes),
        "team_intelligence": {
            "home": home_intel.__dict__,
            "away": away_intel.__dict__,
        },
        "injury_impact": {
            "home": home_injury.__dict__,
            "away": away_injury.__dict__,
        },
        "lineup_strength": {
            "home": home_lineup.__dict__,
            "away": away_lineup.__dict__,
        },
        "odds_intelligence": odds_intel.__dict__,
        "tactical_signals": tactical.__dict__,
        "schedule_fatigue": {
            "home": home_fatigue.__dict__,
            "away": away_fatigue.__dict__,
        },
        "market_movement": {
            "has_history": movement.has_history,
            "points": movement.points,
            "movement": movement.movement,
            "volatility": movement.volatility,
            "direction": movement.direction,
        },
    }
    payload_dict = {"meta": meta}
    prediction = build_prediction(payload_dict)
    meta["model_prediction"] = prediction.__dict__

    return FootballFeatures(
        match=match,
        lineups=lineups,
        injuries=injuries,
        last6=last6,
        h2h=h2h[:h2h_n],
        odds=odds_quotes,
        meta=meta,
    )


def build_features_payload(
    match_id: str,
    stats: FootballStatsProvider,
    odds: FootballOddsProvider,
    *,
    last_n: int = 6,
    h2h_n: int = 6,
) -> dict[str, Any]:
    """
    Build football features and return them as a plain dict payload.
    """
    features = build_features(
        match_id=match_id,
        stats=stats,
        odds=odds,
        last_n=last_n,
        h2h_n=h2h_n,
    )
    return asdict_deep(features)

