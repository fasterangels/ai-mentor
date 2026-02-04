# Dev tools

## Local SQLite reset (`reset_local_db.py`)

**When to run:** After schema changes (e.g. new or altered columns in `models/`) if you are **not** using migrations. If the app or `create_schema.py` reports a schema mismatch (e.g. `table snapshot_resolutions has no column named created_at_utc`), run the reset.

**What it does:** Deletes the configured local SQLite database file and recreates the schema from the current models (`Base.metadata.create_all`). **All local data in that DB is wiped.**

**Requirements:** `DATABASE_URL` must point to a **SQLite file** (e.g. `sqlite+aiosqlite:///./app.db`). The script refuses to run for in-memory or non-SQLite URLs.

**Usage (from backend dir):**
```bash
cd backend
python -m tools.reset_local_db
```

On success it prints: `OK: reset complete`.

This is for **local/dev only**, not a production migration system.
