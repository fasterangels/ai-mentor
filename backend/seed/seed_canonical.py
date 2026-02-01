"""
Minimal deterministic seed for canonical tables (competitions, teams, team_aliases, matches).
Idempotent: upsert by PK; aliases unique by (team_id, alias_norm). No network calls.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.competition import Competition
from models.match import Match
from models.team import Team
from models.team_alias import TeamAlias


def _normalize(text: str) -> str:
    """Match resolver normalization: lowercase, trim, remove punctuation, normalize whitespace."""
    if not text:
        return ""
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


# --- Competitions (stable IDs) ---
COMPETITIONS: List[Dict[str, Any]] = [
    {"id": "gr-super-league", "name": "Super League Greece", "country": "Greece", "tier": 1},
    {"id": "eng-premier-league", "name": "Premier League", "country": "England", "tier": 1},
    {"id": "fr-ligue-1", "name": "Ligue 1", "country": "France", "tier": 1},
    {"id": "es-la-liga", "name": "La Liga", "country": "Spain", "tier": 1},
    {"id": "it-serie-a", "name": "Serie A", "country": "Italy", "tier": 1},
    {"id": "de-bundesliga", "name": "Bundesliga", "country": "Germany", "tier": 1},
    {"id": "uefa-champions-league", "name": "UEFA Champions League", "country": "UEFA", "tier": 1},
    {"id": "uefa-europa-league", "name": "UEFA Europa League", "country": "UEFA", "tier": 1},
    {"id": "uefa-conference-league", "name": "UEFA Conference League", "country": "UEFA", "tier": 1},
]

# --- Teams (id, name, country) + aliases (alias strings; alias_norm computed) ---
TEAMS_WITH_ALIASES: List[Tuple[Dict[str, Any], List[str]]] = [
    ({"id": "paok", "name": "PAOK", "country": "Greece"}, ["PAOK", "ΠΑΟΚ", "παοκ", "Paok"]),
    ({"id": "aek", "name": "AEK", "country": "Greece"}, ["AEK", "ΑΕΚ", "αεκ", "Aek"]),
    ({"id": "olympiacos", "name": "Olympiacos", "country": "Greece"}, ["Olympiacos", "Olympiakos", "ΟΛΥΜΠΙΑΚΟΣ", "ολυμπιακος", "OLYMPIACOS"]),
    ({"id": "panathinaikos", "name": "Panathinaikos", "country": "Greece"}, ["Panathinaikos", "ΠΑΝΑΘΗΝΑΪΚΟΣ", "παναθηναϊκος", "PANATHINAIKOS", "Panathinaikos"]),
    ({"id": "aris", "name": "Aris", "country": "Greece"}, ["Aris", "ΑΡΗΣ", "αρης", "ARIS"]),
    ({"id": "man-united", "name": "Manchester United", "country": "England"}, ["Manchester United", "Man United", "Man Utd", "MUFC", "man united"]),
    ({"id": "liverpool", "name": "Liverpool", "country": "England"}, ["Liverpool", "liverpool"]),
    ({"id": "man-city", "name": "Manchester City", "country": "England"}, ["Manchester City", "Man City", "Man City", "man city"]),
    ({"id": "arsenal", "name": "Arsenal", "country": "England"}, ["Arsenal", "arsenal"]),
    ({"id": "chelsea", "name": "Chelsea", "country": "England"}, ["Chelsea", "chelsea"]),
    ({"id": "barcelona", "name": "Barcelona", "country": "Spain"}, ["Barcelona", "Barca", "barcelona"]),
    ({"id": "real-madrid", "name": "Real Madrid", "country": "Spain"}, ["Real Madrid", "real madrid"]),
    ({"id": "atletico-madrid", "name": "Atletico Madrid", "country": "Spain"}, ["Atletico Madrid", "Atletico", "atletico madrid"]),
    ({"id": "juventus", "name": "Juventus", "country": "Italy"}, ["Juventus", "Juve", "juventus"]),
    ({"id": "inter", "name": "Inter", "country": "Italy"}, ["Inter", "Inter Milan", "inter"]),
    ({"id": "milan", "name": "Milan", "country": "Italy"}, ["Milan", "AC Milan", "milan"]),
    ({"id": "bayern-munich", "name": "Bayern Munich", "country": "Germany"}, ["Bayern Munich", "Bayern", "bayern munich"]),
    ({"id": "dortmund", "name": "Borussia Dortmund", "country": "Germany"}, ["Borussia Dortmund", "Dortmund", "dortmund"]),
    ({"id": "psg", "name": "Paris Saint-Germain", "country": "France"}, ["Paris Saint-Germain", "PSG", "psg"]),
    ({"id": "marseille", "name": "Marseille", "country": "France"}, ["Marseille", "OM", "marseille"]),
]

# --- Matches: id, competition_id, season_id, kickoff_utc, status, home_team_id, away_team_id (scores null)
# TODO: Dev-only fixtures; not real data.
MATCHES: List[Dict[str, Any]] = [
    {"id": "gr-1", "competition_id": "gr-super-league", "kickoff_utc": "2026-02-01T18:00:00+00:00", "status": "SCHEDULED", "home_team_id": "paok", "away_team_id": "aek"},
    {"id": "gr-2", "competition_id": "gr-super-league", "kickoff_utc": "2026-02-08T19:30:00+00:00", "status": "SCHEDULED", "home_team_id": "olympiacos", "away_team_id": "panathinaikos"},
    {"id": "gr-3", "competition_id": "gr-super-league", "kickoff_utc": "2026-02-15T17:00:00+00:00", "status": "SCHEDULED", "home_team_id": "aris", "away_team_id": "paok"},
    {"id": "gr-4", "competition_id": "gr-super-league", "kickoff_utc": "2025-12-01T18:00:00+00:00", "status": "FINISHED", "home_team_id": "aek", "away_team_id": "olympiacos"},
    {"id": "gr-5", "competition_id": "gr-super-league", "kickoff_utc": "2025-11-20T19:00:00+00:00", "status": "FINISHED", "home_team_id": "panathinaikos", "away_team_id": "aris"},
    {"id": "eng-1", "competition_id": "eng-premier-league", "kickoff_utc": "2026-03-01T15:00:00+00:00", "status": "SCHEDULED", "home_team_id": "man-united", "away_team_id": "liverpool"},
    {"id": "eng-2", "competition_id": "eng-premier-league", "kickoff_utc": "2026-03-08T12:30:00+00:00", "status": "SCHEDULED", "home_team_id": "man-city", "away_team_id": "arsenal"},
    {"id": "eng-3", "competition_id": "eng-premier-league", "kickoff_utc": "2026-03-15T17:30:00+00:00", "status": "SCHEDULED", "home_team_id": "chelsea", "away_team_id": "liverpool"},
    {"id": "eng-4", "competition_id": "eng-premier-league", "kickoff_utc": "2025-12-15T15:00:00+00:00", "status": "FINISHED", "home_team_id": "liverpool", "away_team_id": "man-united"},
    {"id": "es-1", "competition_id": "es-la-liga", "kickoff_utc": "2026-02-14T20:00:00+00:00", "status": "SCHEDULED", "home_team_id": "barcelona", "away_team_id": "real-madrid"},
    {"id": "es-2", "competition_id": "es-la-liga", "kickoff_utc": "2026-02-21T18:30:00+00:00", "status": "SCHEDULED", "home_team_id": "atletico-madrid", "away_team_id": "barcelona"},
    {"id": "it-1", "competition_id": "it-serie-a", "kickoff_utc": "2026-02-28T19:45:00+00:00", "status": "SCHEDULED", "home_team_id": "juventus", "away_team_id": "inter"},
    {"id": "it-2", "competition_id": "it-serie-a", "kickoff_utc": "2026-03-07T20:00:00+00:00", "status": "SCHEDULED", "home_team_id": "milan", "away_team_id": "juventus"},
    {"id": "de-1", "competition_id": "de-bundesliga", "kickoff_utc": "2026-03-14T18:30:00+00:00", "status": "SCHEDULED", "home_team_id": "bayern-munich", "away_team_id": "dortmund"},
    {"id": "uefa-1", "competition_id": "uefa-champions-league", "kickoff_utc": "2026-04-01T20:00:00+00:00", "status": "SCHEDULED", "home_team_id": "barcelona", "away_team_id": "man-city"},
    {"id": "uefa-2", "competition_id": "uefa-champions-league", "kickoff_utc": "2026-04-08T20:00:00+00:00", "status": "SCHEDULED", "home_team_id": "real-madrid", "away_team_id": "bayern-munich"},
]


async def seed_canonical(session: AsyncSession) -> Dict[str, Any]:
    """
    Idempotent seed: upsert competitions, teams, aliases (unique by team_id+alias_norm), matches.
    Returns counts: competitions_inserted, teams_inserted, aliases_inserted, matches_inserted.
    """
    counts = {
        "competitions_inserted": 0,
        "teams_inserted": 0,
        "aliases_inserted": 0,
        "matches_inserted": 0,
    }

    # --- Competitions ---
    for row in COMPETITIONS:
        existing = await session.get(Competition, row["id"])
        if existing is None:
            session.add(Competition(
                id=row["id"],
                name=row["name"],
                country=row["country"],
                tier=row.get("tier", 1),
                is_active=True,
            ))
            counts["competitions_inserted"] += 1

    # --- Teams + Aliases ---
    for team_row, alias_strings in TEAMS_WITH_ALIASES:
        tid = team_row["id"]
        existing_team = await session.get(Team, tid)
        if existing_team is None:
            session.add(Team(
                id=tid,
                name=team_row["name"],
                country=team_row["country"],
                is_active=True,
            ))
            counts["teams_inserted"] += 1

        seen_norm: set[str] = set()
        for alias in alias_strings:
            norm = _normalize(alias)
            if not norm or norm in seen_norm:
                continue
            seen_norm.add(norm)
            stmt = select(TeamAlias).where(
                TeamAlias.team_id == tid,
                TeamAlias.alias_norm == norm,
            )
            r = await session.execute(stmt)
            if r.scalar_one_or_none() is None:
                session.add(TeamAlias(
                    team_id=tid,
                    alias=alias,
                    alias_norm=norm,
                    language="und",
                    quality=1.0,
                ))
                counts["aliases_inserted"] += 1

    # --- Matches ---
    for row in MATCHES:
        existing = await session.get(Match, row["id"])
        if existing is None:
            kickoff = row["kickoff_utc"]
            if isinstance(kickoff, str):
                kickoff = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            session.add(Match(
                id=row["id"],
                competition_id=row["competition_id"],
                season_id=None,
                kickoff_utc=kickoff,
                status=row["status"],
                home_team_id=row["home_team_id"],
                away_team_id=row["away_team_id"],
                home_score=None,
                away_score=None,
            ))
            counts["matches_inserted"] += 1

    return counts
