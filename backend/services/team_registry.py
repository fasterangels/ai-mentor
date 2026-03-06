from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _BACKEND_ROOT / "data"


def _load_json(filename: str) -> Any:
  """Load a JSON file from backend/data, returning [] or {} on failure."""
  path = _DATA_DIR / filename
  try:
    with path.open("r", encoding="utf-8") as f:
      return json.load(f)
  except FileNotFoundError:
    return []


@lru_cache(maxsize=1)
def load_teams() -> List[Dict[str, Any]]:
  """Load all team records from teams.json."""
  data = _load_json("teams.json")
  return list(data) if isinstance(data, list) else []


@lru_cache(maxsize=1)
def load_leagues() -> List[Dict[str, Any]]:
  """Load all league records from leagues.json."""
  data = _load_json("leagues.json")
  return list(data) if isinstance(data, list) else []


@lru_cache(maxsize=1)
def _team_index() -> Dict[str, Dict[str, Any]]:
  """Build a lookup index for teams by id, name, and aliases (case-insensitive)."""
  index: Dict[str, Dict[str, Any]] = {}
  for team in load_teams():
    tid = str(team.get("id") or "").strip()
    name = str(team.get("name") or "").strip()
    aliases = team.get("aliases") or []

    keys: List[str] = []
    if tid:
      keys.append(tid.lower())
    if name:
      keys.append(name.lower())
    for alias in aliases:
      if isinstance(alias, str) and alias.strip():
        keys.append(alias.strip().lower())

    for k in keys:
      index.setdefault(k, team)
  return index


def resolve_team(name: str) -> Optional[Dict[str, Any]]:
  """Resolve a team by id, name, or alias (case-insensitive).

  Returns the full team record dict, or None if unknown.
  """
  if not name:
    return None
  key = str(name).strip().lower()
  if not key:
    return None
  return _team_index().get(key)


@lru_cache(maxsize=1)
def _league_index() -> Dict[str, Dict[str, Any]]:
  """Build a lookup index for leagues by id and name (case-insensitive)."""
  index: Dict[str, Dict[str, Any]] = {}
  for league in load_leagues():
    lid = str(league.get("id") or "").strip()
    name = str(league.get("name") or "").strip()
    keys: List[str] = []
    if lid:
      keys.append(lid.lower())
    if name:
      keys.append(name.lower())
    for k in keys:
      index.setdefault(k, league)
  return index


def resolve_league(name: str) -> Optional[Dict[str, Any]]:
  """Resolve a league by id or name (case-insensitive).

  Returns the full league record dict, or None if unknown.
  """
  if not name:
    return None
  key = str(name).strip().lower()
  if not key:
    return None
  return _league_index().get(key)

