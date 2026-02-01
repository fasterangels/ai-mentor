from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.team import Team
from repositories.match_repo import MatchRepository
from repositories.team_repo import TeamRepository
from .types import MatchCandidate, MatchResolutionInput, MatchResolutionOutput


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, trim, remove punctuation."""
    if not text:
        return ""
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


async def _resolve_team(
    text: str, team_repo: TeamRepository
) -> tuple[Optional[Team], List[str]]:
    """
    Resolve a team from text input.

    Returns:
        (Team | None, notes[])
    """
    normalized = _normalize(text)
    if not normalized:
        return None, ["TEAM_TEXT_EMPTY"]

    all_teams = await team_repo.list_active()

    exact_matches = [
        team for team in all_teams if _normalize(team.name) == normalized
    ]

    if len(exact_matches) == 1:
        return exact_matches[0], []

    if len(exact_matches) > 1:
        return None, [f"TEAM_AMBIGUOUS_EXACT_MATCH ({len(exact_matches)} teams)"]

    alias_match = await team_repo.find_by_alias(normalized)
    if alias_match:
        return alias_match, []

    return None, ["TEAM_NOT_FOUND"]


async def resolve_match(
    input_data: MatchResolutionInput, session: AsyncSession
) -> MatchResolutionOutput:
    """
    Resolve user input into a canonical Match.
    """
    team_repo = TeamRepository(session)
    match_repo = MatchRepository(session)

    notes: List[str] = []

    # --- STEP 1: Resolve teams ---
    home_team, home_notes = await _resolve_team(input_data.home_text, team_repo)
    notes.extend([f"HOME_{n}" for n in home_notes])

    away_team, away_notes = await _resolve_team(input_data.away_text, team_repo)
    notes.extend([f"AWAY_{n}" for n in away_notes])

    if any("AMBIGUOUS" in n for n in home_notes + away_notes):
        return MatchResolutionOutput(
            status="AMBIGUOUS",
            notes=notes,
        )

    if home_team is None or away_team is None:
        return MatchResolutionOutput(
            status="NOT_FOUND",
            notes=notes,
        )

    # --- STEP 2: Kickoff window ---
    if input_data.kickoff_hint_utc:
        kickoff_hint = input_data.kickoff_hint_utc
        if isinstance(kickoff_hint, str):
            kickoff_hint = datetime.fromisoformat(
                kickoff_hint.replace("Z", "+00:00")
            )
        if kickoff_hint.tzinfo is None:
            kickoff_hint = kickoff_hint.replace(tzinfo=timezone.utc)

        delta = timedelta(hours=input_data.window_hours)
        kickoff_from = kickoff_hint - delta
        kickoff_to = kickoff_hint + delta
    else:
        now = datetime.now(timezone.utc)
        delta = timedelta(hours=72)
        kickoff_from = now - delta
        kickoff_to = now + delta
        notes.append("NO_KICKOFF_HINT_USING_BOUNDED_WINDOW")

    # --- STEP 3: Find matches ---
    if input_data.competition_id:
        matches = await match_repo.find_by_competition_and_kickoff(
            input_data.competition_id,
            kickoff_from,
            kickoff_to,
        )
        matches = [
            m
            for m in matches
            if m.home_team_id == home_team.id
            and m.away_team_id == away_team.id
        ]
    else:
        matches = await match_repo.find_by_teams_and_kickoff(
            home_team.id,
            away_team.id,
            kickoff_from,
            kickoff_to,
        )

    # --- STEP 4: Decide outcome ---
    if len(matches) == 0:
        notes.append("NO_MATCH_IN_WINDOW")
        return MatchResolutionOutput(
            status="NOT_FOUND",
            notes=notes,
        )

    if len(matches) == 1:
        match = matches[0]

        if not match.id:
            return MatchResolutionOutput(
                status="NOT_FOUND",
                match_id=None,
                candidates=None,
                notes=notes + ["RESOLVED_WITHOUT_MATCH_ID_GUARD"],
            )

        return MatchResolutionOutput(
            status="RESOLVED",
            match_id=match.id,
            candidates=None,
            notes=notes,
        )

    # --- Multiple matches ---
    notes.append(f"MULTIPLE_MATCHES_IN_WINDOW ({len(matches)} matches)")
    candidates = [
        MatchCandidate(
            match_id=m.id,
            kickoff_utc=m.kickoff_utc,
            competition_id=m.competition_id,
        )
        for m in matches
    ]

    return MatchResolutionOutput(
        status="AMBIGUOUS",
        candidates=candidates,
        notes=notes,
    )