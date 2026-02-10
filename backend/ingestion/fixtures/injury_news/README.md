# Injury/News recorded fixtures

JSON artifacts for the recorded injury/news adapter (`recorded_injury_news_v1`). Each file is one report.

## Schema (per file)

- `source_ref`: string (required)
- `published_at`: ISO8601 optional
- `title`: string optional
- `body`: string optional
- `claims`: array of claim objects (required)

Each claim:
- `team_ref`: string (required)
- `player_ref`: string optional
- `claim_type`: INJURY_STATUS | SUSPENSION | RETURN
- `status`: OUT | DOUBTFUL | FIT | SUSPENDED | UNKNOWN
- `validity`: NEXT_MATCH | DATE | RANGE | UNKNOWN
- `valid_from` / `valid_to`: ISO8601 optional
- `confidence`: 0.0–1.0
- `evidence_ptr`: string or object optional

Files are loaded in sorted order (deterministic).
