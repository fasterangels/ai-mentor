"""
Late-data scenario storage (I1 Part A).
Writes to reports/replay_scenarios/late_data/ with deterministic filenames.
No deletes outside reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

# Default root under reports
LATE_DATA_SCENARIOS_DIR = "reports/replay_scenarios/late_data"
SCENARIO_FILE_SUFFIX = ".json"


def scenario_filename(scenario_id: str) -> str:
    """Deterministic filename for a scenario (no path)."""
    return f"{scenario_id}{SCENARIO_FILE_SUFFIX}"


def write_scenario(output_dir: Union[Path, str], scenario_id: str, payload_json: str) -> Path:
    """
    Write one scenario file. Filename = {scenario_id}.json.
    Content = payload_json (metadata + payload) unchanged.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / scenario_filename(scenario_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload_json)
    return path
