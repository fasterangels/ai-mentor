"""
Generate a new RecordedPlatformAdapter skeleton and fixtures.
Usage: python tools/new_platform_adapter.py --name bet365_like [--out backend/ingestion/connectors]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _sanitize_name(name: str) -> str:
    """Alphanumeric and underscores only."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_") or "adapter"


def _module_name(name: str) -> str:
    return _sanitize_name(name).lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate platform adapter skeleton")
    parser.add_argument("--name", required=True, help="Adapter name (e.g. bet365_like)")
    parser.add_argument(
        "--out",
        default="backend/ingestion/connectors",
        help="Output directory for connector module (default: backend/ingestion/connectors)",
    )
    args = parser.parse_args()

    name = _module_name(args.name)
    if not name:
        print("Invalid --name", file=sys.stderr)
        return 1

    out = Path(args.out)
    # Resolve backend root: out is e.g. backend/ingestion/connectors -> backend
    backend = out.resolve()
    for _ in range(2):
        backend = backend.parent
    ingestion = backend / "ingestion"
    fixtures_base = ingestion / "fixtures"
    tests_dir = backend / "tests"

    connector_path = out / f"{name}.py"
    fixtures_dir = fixtures_base / name
    readme_path = fixtures_dir / "README.md"
    example_path = fixtures_dir / "example_1.json"
    test_path = tests_dir / f"test_{name}_adapter_contract.py"

    # Skeleton adapter
    class_name = "".join(w.capitalize() for w in name.split("_")) + "Adapter"
    connector_content = f'''"""
{name} platform adapter: recorded fixtures only, no HTTP.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ingestion.connectors.platform_base import (
    IngestedMatchData,
    MatchIdentity,
    RecordedPlatformAdapter,
)


def _normalize_kickoff_utc(value: str) -> str:
    """Normalize kickoff to ISO8601 UTC. Raises ValueError if missing or invalid."""
    from datetime import datetime, timezone
    if not value or not isinstance(value, str):
        raise ValueError("kickoff_utc is required and must be a non-empty string")
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"kickoff_utc must be ISO8601: {{e!s}}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_odds_1x2(raw: Any) -> Dict[str, float]:
    """Extract 1X2 odds. Required keys: home, draw, away."""
    if not isinstance(raw, dict):
        raise ValueError("odds_1x2 must be an object with home, draw, away")
    required = ("home", "draw", "away")
    for k in required:
        if k not in raw:
            raise ValueError(f"odds_1x2 missing required key: {{k!r}}")
    return {{k: float(raw[k]) for k in required}}


class {class_name}(RecordedPlatformAdapter):
    """Adapter that reads fixtures from ingestion/fixtures/{name}/*.json."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        if fixtures_dir is None:
            base = Path(__file__).resolve().parent.parent.parent
            fixtures_dir = base / "ingestion" / "fixtures" / "{name}"
        self._fixtures_dir = Path(fixtures_dir)

    @property
    def name(self) -> str:
        return "{name}"

    def load_fixtures(self) -> List[Dict[str, Any]]:
        if not self._fixtures_dir.exists():
            return []
        fixtures: List[Dict[str, Any]] = []
        for path in sorted(self._fixtures_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    fixtures.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return fixtures

    def parse_fixture(self, raw: Dict[str, Any]) -> IngestedMatchData:
        match_id = str(raw.get("match_id") or raw.get("id") or "").strip()
        if not match_id:
            raise ValueError("match_id is required")
        home_team = str(raw.get("home_team") or "").strip()
        if not home_team:
            raise ValueError("home_team is required")
        away_team = str(raw.get("away_team") or "").strip()
        if not away_team:
            raise ValueError("away_team is required")
        competition = str(raw.get("competition") or "").strip()
        if not competition:
            raise ValueError("competition is required")
        kickoff_utc = _normalize_kickoff_utc(str(raw.get("kickoff_utc") or ""))
        odds_1x2 = _parse_odds_1x2(raw.get("odds_1x2"))
        status = str(raw.get("status") or "scheduled").strip()
        return IngestedMatchData(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            kickoff_utc=kickoff_utc,
            odds_1x2=odds_1x2,
            status=status,
        )
'''

    readme_content = f"""# {name} fixture schema

Fixtures are JSON files consumed by `{class_name}`. No live network calls.

## Required fields

- `match_id` (string)
- `home_team`, `away_team`, `competition` (strings)
- `kickoff_utc` (ISO8601, normalized to UTC)
- `odds_1x2`: object with `home`, `draw`, `away` (decimal odds > 0)
- `status` (string)
"""

    example_content = """{
  "match_id": "example_1",
  "home_team": "Team A",
  "away_team": "Team B",
  "competition": "Example League",
  "kickoff_utc": "2025-10-01T20:00:00+00:00",
  "status": "scheduled",
  "odds_1x2": {
    "home": 2.0,
    "draw": 3.5,
    "away": 3.2
  }
}
"""

    test_content = f'''"""Contract tests for {name} adapter."""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from tests.contract.test_platform_adapter_contract import assert_adapter_contract


def test_{name}_adapter_contract() -> None:
    assert_adapter_contract("{name}", "ingestion/fixtures/{name}")
'''

    connector_path.parent.mkdir(parents=True, exist_ok=True)
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    connector_path.write_text(connector_content, encoding="utf-8")
    readme_path.write_text(readme_content, encoding="utf-8")
    example_path.write_text(example_content.strip() + "\n", encoding="utf-8")
    test_path.write_text(test_content, encoding="utf-8")

    print(f"Created: {connector_path}")
    print(f"Created: {readme_path}")
    print(f"Created: {example_path}")
    print(f"Created: {test_path}")
    print()
    print("Registry: add to backend/ingestion/registry.py:")
    print(f'  from ingestion.connectors.{name} import {class_name}')
    print(f'  _REGISTRY["{name}"] = {class_name}()')
    return 0


if __name__ == "__main__":
    sys.exit(main())
