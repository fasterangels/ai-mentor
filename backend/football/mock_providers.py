from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

from .models import H2HItem, Injury, LastMatch, LineupPlayer, MatchRef, OddsQuote, TeamRef
from .providers import FootballOddsProvider, FootballStatsProvider


@dataclass
class MockFootballStatsProvider(FootballStatsProvider):
    """
    Deterministic in-memory stats provider for football feature building.
    """

    name: str = "mock_stats"

    def get_match(self, match_id: str) -> MatchRef:
        home = TeamRef(team_id="T_HOME", name="Home FC")
        away = TeamRef(team_id="T_AWAY", name="Away FC")
        return MatchRef(
            match_id=match_id,
            league="DEMO",
            kickoff_iso="2026-01-01T18:00:00Z",
            home=home,
            away=away,
        )

    def get_lineups(self, match_id: str) -> List[LineupPlayer]:
        match = self.get_match(match_id)
        players: List[LineupPlayer] = []
        # 11 starters per team with stable names.
        for i in range(1, 12):
            players.append(
                LineupPlayer(
                    team_id=match.home.team_id,
                    player=f"{match.home.name}_Player_{i}",
                    role="starter",
                )
            )
        for i in range(1, 12):
            players.append(
                LineupPlayer(
                    team_id=match.away.team_id,
                    player=f"{match.away.name}_Player_{i}",
                    role="starter",
                )
            )
        return players

    def get_injuries(self, match_id: str) -> List[Injury]:
        match = self.get_match(match_id)
        # One deterministic injury for the away team only.
        return [
            Injury(
                team_id=match.away.team_id,
                player="Away Key Player",
                type="injury",
                status="out",
            )
        ]

    def get_last_matches(self, team_id: str, n: int = 6) -> List[LastMatch]:
        # Cycle through W/D/L based on team_id-derived offset.
        pattern = ["W", "D", "L"]
        offset = sum(ord(c) for c in team_id) % len(pattern)

        base_date = datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        results: List[LastMatch] = []
        for i in range(n):
            result = pattern[(offset + i) % len(pattern)]
            date = base_date - timedelta(days=i * 3)
            results.append(
                LastMatch(
                    team_id=team_id,
                    opponent=f"Opponent_{i+1}",
                    result=result,
                    date_iso=date.isoformat(),
                )
            )
        return results

    def get_h2h(self, home_team_id: str, away_team_id: str, n: int = 6) -> List[H2HItem]:
        # Stable goal patterns over n matches.
        base_date = datetime(2024, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        items: List[H2HItem] = []
        for i in range(n):
            home_goals = i % 3
            away_goals = (2 - i) % 3
            date = base_date - timedelta(days=i * 7)
            items.append(
                H2HItem(
                    home_goals=home_goals,
                    away_goals=away_goals,
                    date_iso=date.isoformat(),
                )
            )
        return items


@dataclass
class MockFootballOddsProvider(FootballOddsProvider):
    """
    Deterministic odds provider for football matches.
    """

    name: str = "mock_odds"

    def get_odds(self, match_id: str) -> List[OddsQuote]:
        # 1x2 market with three stable outcomes.
        return [
            OddsQuote(
                bookmaker="MockBook",
                market="1x2",
                outcome="home",
                price=1.90,
            ),
            OddsQuote(
                bookmaker="MockBook",
                market="1x2",
                outcome="draw",
                price=3.40,
            ),
            OddsQuote(
                bookmaker="MockBook",
                market="1x2",
                outcome="away",
                price=4.10,
            ),
        ]

