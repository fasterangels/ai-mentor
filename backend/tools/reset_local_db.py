"""
Reset local SQLite database: delete file and recreate schema from models.
For local/dev only. Refuses to run if DATABASE_URL is not SQLite file-based.
Usage: python -m tools.reset_local_db (from backend dir) or python backend/tools/reset_local_db.py (from repo root).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from repo root or backend
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from core.config import get_settings
from core.database import init_database, dispose_database, get_database_manager
from models.base import Base
import models  # noqa: F401 - register all models


def _get_sqlite_path(database_url: str) -> Path | None:
    """Extract SQLite file path from URL. Returns None if not sqlite file (e.g. :memory: or non-sqlite)."""
    url = (database_url or "").strip()
    if not url.startswith("sqlite"):
        return None
    if ":memory:" in url:
        return None
    # sqlite+aiosqlite:///./app.db or sqlite+aiosqlite:///C:/path/to/db
    try:
        from sqlalchemy.engine import make_url
        u = make_url(url)
        db = (getattr(u, "database", None) or "").strip()
        if not db:
            return None
        return Path(db)
    except Exception:
        return None


async def _main() -> int:
    settings = get_settings()
    url = settings.database_url or ""

    if "sqlite" not in url.lower():
        print("Refusing: DATABASE_URL is not SQLite. Reset is only for local SQLite file DBs.", file=sys.stderr)
        return 1

    path = _get_sqlite_path(url)
    if path is None:
        print("Refusing: DATABASE_URL appears to be in-memory or invalid. Use a file path for reset.", file=sys.stderr)
        return 1

    path = path.resolve()
    if path.exists():
        try:
            path.unlink()
        except OSError as e:
            print(f"Failed to delete database file {path}: {e}", file=sys.stderr)
            return 1

    await init_database(url)
    engine = get_database_manager().engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await dispose_database()

    print("OK: reset complete")
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
