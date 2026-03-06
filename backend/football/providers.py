from __future__ import annotations

from typing import List, Protocol

from .models import H2HItem, Injury, LastMatch, LineupPlayer, MatchRef, OddsQuote


class FootballStatsProvider(Protocol):
    name: str

    def get_match(self, match_id: str) -> MatchRef:
        ...

    def get_lineups(self, match_id: str) -> List[LineupPlayer]:
        ...

    def get_injuries(self, match_id: str) -> List[Injury]:
        ...

    def get_last_matches(self, team_id: str, n: int = 6) -> List[LastMatch]:
        ...

    def get_h2h(self, home_team_id: str, away_team_id: str, n: int = 6) -> List[H2HItem]:
        ...


class FootballOddsProvider(Protocol):
    name: str

    def get_odds(self, match_id: str) -> List[OddsQuote]:
        ...

