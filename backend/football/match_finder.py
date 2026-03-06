from dataclasses import dataclass
from typing import List


@dataclass
class TeamMatch:
    match_id: str
    home: str
    away: str
    league: str
    kickoff_iso: str


# Words that may appear in a query but are not team names (ignored when matching).
_STOPWORDS = frozenset({"vs", "v", "versus"})


def find_match_by_teams(query: str, fixtures: List[TeamMatch]) -> TeamMatch | None:
    q = query.lower()
    words = [w for w in q.split() if w and w not in _STOPWORDS]

    for f in fixtures:
        text = f"{f.home} {f.away}".lower()

        if words and all(word in text for word in words):
            return f

    return None


def find_matches_by_team(team: str, fixtures: List[TeamMatch]) -> List[TeamMatch]:
    t = team.lower()

    results = []

    for f in fixtures:
        if t in f.home.lower() or t in f.away.lower():
            results.append(f)

    return results
