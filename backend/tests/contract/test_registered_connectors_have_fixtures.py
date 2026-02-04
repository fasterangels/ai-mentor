"""
CI: every registered platform connector must have a fixtures directory.
Fails if a connector is registered without backend/ingestion/fixtures/<name>/.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from ingestion.registry import list_registered_connectors


def test_every_registered_connector_has_fixtures_dir() -> None:
    """Each registered connector must have ingestion/fixtures/<name>/ directory."""
    fixtures_base = _backend / "ingestion" / "fixtures"
    missing: list[str] = []
    for name in list_registered_connectors():
        path = fixtures_base / name
        if not path.is_dir():
            missing.append(name)
    assert not missing, (
        f"Registered connector(s) missing fixtures directory: {missing}. "
        f"Create backend/ingestion/fixtures/<name>/ with at least one JSON fixture and a README."
    )
