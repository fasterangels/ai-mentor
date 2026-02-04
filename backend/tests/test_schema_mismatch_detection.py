"""
Test schema mismatch detection: stale snapshot_resolutions (missing created_at_utc) is detected.
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

import models  # noqa: F401 - register snapshot_resolutions on Base.metadata
from tools.schema_check import check_sqlite_schema_mismatch


def test_schema_mismatch_detection_triggers_when_column_missing(tmp_path: Path) -> None:
    """Create SQLite DB with snapshot_resolutions missing created_at_utc; detection returns True."""
    # Use file DB so multiple connections see the same schema (in-memory is per-connection)
    db_file = tmp_path / "stale.db"
    engine: Engine = create_engine(f"sqlite:///{db_file}")

    with engine.connect() as conn:
        # Create a stale table (e.g. old schema without created_at_utc)
        conn.execute(text("""
            CREATE TABLE snapshot_resolutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_run_id INTEGER NOT NULL,
                match_id VARCHAR NOT NULL,
                final_home_goals INTEGER NOT NULL,
                final_away_goals INTEGER NOT NULL,
                status VARCHAR NOT NULL,
                market_outcomes_json TEXT NOT NULL,
                reason_codes_by_market_json TEXT NOT NULL,
                FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs(id)
            )
        """))
        conn.commit()

    has_mismatch, message = check_sqlite_schema_mismatch(engine)
    assert has_mismatch is True
    assert "created_at_utc" in message or "missing" in message.lower()
    assert "reset_local_db" in message or "reset" in message.lower()


def test_schema_ok_when_table_does_not_exist() -> None:
    """When snapshot_resolutions does not exist, no mismatch reported."""
    engine = create_engine("sqlite:///:memory:")
    has_mismatch, message = check_sqlite_schema_mismatch(engine)
    assert has_mismatch is False
    assert message == ""
