"""
Detect SQLite schema mismatch (e.g. stale table missing columns).
Used by create_schema to warn and exit non-zero instead of failing later at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from models.base import Base

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


def check_sqlite_schema_mismatch(sync_engine: "Engine") -> Tuple[bool, str]:
    """
    Check if snapshot_resolutions table exists but is missing columns expected by the model.
    Returns (has_mismatch, message). has_mismatch True means current schema is stale.
    """
    table_name = "snapshot_resolutions"
    if table_name not in Base.metadata.tables:
        return False, ""

    expected_columns = set(Base.metadata.tables[table_name].columns.keys())

    from sqlalchemy import inspect
    inspector = inspect(sync_engine)
    if not inspector.has_table(table_name):
        return False, ""

    current_columns = {c["name"] for c in inspector.get_columns(table_name)}
    missing = expected_columns - current_columns
    if missing:
        return True, (
            f"Table {table_name!r} exists but is missing column(s): {sorted(missing)}. "
            "Run: python -m tools.reset_local_db (from backend dir) to reset the local DB and recreate schema."
        )
    return False, ""
