# Sample platform fixture schema

Fixtures in this folder are JSON files consumed by `SamplePlatformAdapter`. No live network calls; all data is recorded.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | string | Unique match identifier (used in pipeline as match_id). |
| `home_team` | string | Home team name. |
| `away_team` | string | Away team name. |
| `competition` | string | Competition or league name. |
| `kickoff_utc` | string | ISO8601 kickoff time (e.g. `2025-09-15T19:00:00+00:00` or `...Z`). Normalized to UTC. |
| `odds_1x2` | object | Decimal odds for 1X2 market. Must have keys: `home`, `draw`, `away`. |
| `status` | string | Match state: e.g. `scheduled`, `in_play`, `finished`. |

## Optional fields

- `venue`: string
- `id`: alternative to `match_id` for lookup (adapter uses `match_id` first)

## Odds mapping

- External keys `home`, `draw`, `away` map to internal 1X2 selections as-is.
- Values are decimal odds (e.g. 2.10 for home).

## Timestamps

- `kickoff_utc` is normalized to UTC; `Z` and `+00:00` are accepted.
- No heuristics; if the field is missing or invalid, the adapter raises `ValueError`.
