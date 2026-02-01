# Canonical DB schema & migrations

This backend now has a **canonical SQLAlchemy 2.0 model set** under `backend/models/`
for the offline‑first football analyzer. These models intentionally **do not**
replace or refactor the legacy `backend/models.py` / `backend/analytics_models.py`
yet – they are a clean schema foundation only.

> NOTE: There is an existing `backend/models.py` module and a new
> `backend/models/` package. Import paths must be chosen carefully during
> integration to avoid ambiguity. See TODO below.

---

## 1. Alembic status

- Alembic is **not** currently configured in this repository
  (`alembic.ini` / standard migrations folder are absent).
- We will introduce Alembic in a follow‑up block (**TODO**) instead of
  inventing a complex setup here.

### TODO (BLOCK 2.1 – planned)

- Introduce Alembic configured to use:
  - the async engine from `backend/core/database.py` (`DatabaseManager`)
  - the canonical metadata from `backend/models/base.py::Base.metadata`
  - a clear import path for the `backend/models/` package that does **not**
    conflict with the legacy `backend/models.py` module
- Generate an initial migration capturing all canonical tables in
  `backend/models/*.py`.

---

## 2. Temporary schema initialization (no Alembic yet)

Until Alembic is introduced, you can initialize the canonical schema **once**
using `Base.metadata.create_all()` against the existing async engine managed by
`DatabaseManager`. This is a **temporary bootstrap** and should not be used as a
long‑term migration strategy.

From the project root:

```powershell
cd backend
python -c "import asyncio; \
from core.config import get_settings; \
from core.database import init_database, get_database_manager; \
from models import Base  # TODO: ensure this imports the canonical models package, not legacy models.py; adjust PYTHONPATH/imports as needed.; \
async def main(): \
    settings = get_settings(); \
    await init_database(settings.database_url); \
    engine = get_database_manager().engine; \
    assert engine is not None; \
    async with engine.begin() as conn: \
        await conn.run_sync(Base.metadata.create_all); \
asyncio.run(main())"
```

Important notes:

- This uses the **existing** async `DatabaseManager` (no new engine is created).
- It operates on **all tables registered on `Base.metadata`**, which come from
  the canonical models in `backend/models/`.
- Because of the legacy `backend/models.py` module, you may need to adjust
  imports (e.g. importing `Base` from a more explicit path) once a final
  packaging strategy is chosen.

---

## 3. Safety & future direction

- This README does **not** introduce any new migration scripts or engines.
- Schema changes must be coordinated with the planned Alembic setup so that:
  - future migrations are reversible and deterministic
  - legacy tables (if any) can be migrated or deprecated safely
- Until Alembic is in place, avoid destructive schema changes and prefer
  additive changes only.

