"""
Validate fixture directory: required fields, kickoff UTC, odds > 0, unique match_id.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_TOP = ("match_id", "home_team", "away_team", "competition", "kickoff_utc", "odds_1x2", "status")
ODDS_1X2_KEYS = ("home", "draw", "away")


@dataclass
class ValidationReport:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _normalize_kickoff(value: str) -> str | None:
    """Parse and normalize to UTC ISO8601. Returns None if invalid."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (ValueError, TypeError):
        return None


def validate_fixtures(dir_path: str | Path) -> ValidationReport:
    """
    Validate all JSON fixtures in dir_path.
    Rules: required fields (MatchIdentity + 1X2 odds), kickoff parseable to UTC, odds > 0, match_id unique.
    """
    errors: List[str] = []
    warnings: List[str] = []
    path = Path(dir_path)
    if not path.exists() or not path.is_dir():
        return ValidationReport(ok=False, errors=[f"Directory does not exist or is not a directory: {path}"])

    seen_match_ids: set[str] = set()
    files = sorted(path.glob("*.json"))

    if not files:
        warnings.append("No JSON files found in fixture directory")

    for file_path in files:
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f"{file_path.name}: invalid JSON or read error: {e}")
            continue

        if not isinstance(raw, dict):
            errors.append(f"{file_path.name}: root must be a JSON object")
            continue

        # Required top-level fields
        for key in REQUIRED_TOP:
            if key == "match_id":
                mid = raw.get("match_id") or raw.get("id")
                if mid is None:
                    errors.append(f"{file_path.name}: match_id (or id) is required")
                else:
                    mid_str = str(mid).strip()
                    if not mid_str:
                        errors.append(f"{file_path.name}: match_id cannot be empty")
                    elif mid_str in seen_match_ids:
                        errors.append(f"{file_path.name}: duplicate match_id {mid_str!r}")
                    else:
                        seen_match_ids.add(mid_str)
            elif key not in raw:
                errors.append(f"{file_path.name}: missing required field {key!r}")
            elif key == "kickoff_utc":
                k = raw.get("kickoff_utc")
                if k is not None and _normalize_kickoff(str(k)) is None:
                    errors.append(f"{file_path.name}: kickoff_utc must be parseable ISO8601 and normalized to UTC")
            elif key == "odds_1x2":
                odds = raw.get("odds_1x2")
                if isinstance(odds, dict):
                    for ok in ODDS_1X2_KEYS:
                        if ok not in odds:
                            errors.append(f"{file_path.name}: odds_1x2 missing key {ok!r}")
                        else:
                            try:
                                v = float(odds[ok])
                                if v <= 0:
                                    errors.append(f"{file_path.name}: odds_1x2.{ok} must be > 0")
                            except (TypeError, ValueError):
                                errors.append(f"{file_path.name}: odds_1x2.{ok} must be a number > 0")
                elif odds is not None:
                    errors.append(f"{file_path.name}: odds_1x2 must be an object with home, draw, away")

    return ValidationReport(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
