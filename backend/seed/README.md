# Canonical DB Seed

Minimal deterministic seed for canonical tables (competitions, teams, team_aliases, matches) so the Match Resolver can resolve common inputs (Greek/English names) in local dev.

- **No web scraping, no APIs, no external data.** Manual seed only.
- **Idempotent:** Running twice does not duplicate rows (upsert by primary key; aliases unique by `team_id` + `alias_norm`).
- Uses the **existing** `core/database.py` DatabaseManager only (no new engine/sessionmaker).
- Populates the canonical DB file used by `core.config.DATABASE_URL` (default: `./app.db` under backend).

## Prerequisites

- Python environment with backend dependencies installed (`pip install -r requirements.txt`).
- **Backend DB engine does not need to be running;** the seed initializes the DB and runs standalone.

## How to run (PowerShell)

From the **backend** directory:

```powershell
cd backend
python -m seed
```

Alternatively, if running from project root with `backend` on `PYTHONPATH`:

```powershell
python -m backend.seed
```

The seed will:

1. Use `core.config.get_settings()` (and thus `DATABASE_URL`, default `sqlite+aiosqlite:///./app.db`).
2. Call `init_database(settings.database_url)` so the canonical schema can be created if needed (schema creation is done elsewhere, e.g. migrations or app startup).
3. Open a session from the existing DatabaseManager and run `seed_canonical(session)`.
4. Print counts: `competitions_inserted`, `teams_inserted`, `aliases_inserted`, `matches_inserted`.

## Example output

First run:

```
Seed complete: {'competitions_inserted': 9, 'teams_inserted': 20, 'aliases_inserted': 85, 'matches_inserted': 16}
```

Second run (idempotent):

```
Seed complete: {'competitions_inserted': 0, 'teams_inserted': 0, 'aliases_inserted': 0, 'matches_inserted': 0}
```

## What is seeded

- **Competitions:** gr-super-league, eng-premier-league, fr-ligue-1, es-la-liga, it-serie-a, de-bundesliga, uefa-champions-league, uefa-europa-league, uefa-conference-league.
- **Teams + aliases:** Greek (PAOK, AEK, Olympiacos, Panathinaikos, Aris), English (Man United, Liverpool, Man City, Arsenal, Chelsea), Spanish (Barcelona, Real Madrid, Atletico Madrid), Italian (Juventus, Inter, Milan), German (Bayern Munich, Dortmund), French (PSG, Marseille). Aliases include Greek/Latin and short forms (e.g. Man Utd, PSG); `alias_norm` matches resolver normalization.
- **Matches:** 10–20 fixed fixtures (Super League, Premier League, La Liga, Serie A, Bundesliga, UEFA) with stable IDs and `kickoff_utc` in past/future for testing. Dev-only; not real fixtures.

## Notes

- Canonical schema (e.g. `backend/models/`) must exist; create tables first via migrations or `Base.metadata.create_all` if required.
- Legacy DB (`ai_mentor.db`) and legacy models are **not** touched; only canonical tables under `backend/models/` are populated.
