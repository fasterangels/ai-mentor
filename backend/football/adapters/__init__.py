"""
Football API adapters: API-Football (stats) and The Odds API (odds), normalized to domain models.
"""

from .api_football_adapter import ApiFootballStatsProvider
from .odds_api_adapter import OddsApiProvider, parse_odds_response

__all__ = ["ApiFootballStatsProvider", "OddsApiProvider", "parse_odds_response"]
