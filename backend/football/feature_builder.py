from __future__ import annotations

from typing import Any

from .models import FootballFeatures, asdict_deep
from .providers import FootballOddsProvider, FootballStatsProvider


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

    h2h = stats.get_h2h(match.home.team_id, match.away.team_id, n=h2h_n)
    odds_quotes = odds.get_odds(match_id)

    meta = {
        "stats_provider": getattr(stats, "name", type(stats).__name__),
        "odds_provider": getattr(odds, "name", type(odds).__name__),
        "lineup_count": len(lineups),
        "injury_count": len(injuries),
        "last_n": last_n,
        "h2h_n": h2h_n,
        "h2h_count": len(h2h),
        "odds_count": len(odds_quotes),
    }

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

