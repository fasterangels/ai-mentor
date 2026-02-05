# Real provider fixture schema

Fixtures in this folder are JSON files consumed by `RealProviderAdapter` in **recorded mode**. No live network calls unless `REAL_PROVIDER_LIVE=true` and `LIVE_IO_ALLOWED=true` (and required env vars are set).

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | string | Unique match identifier. |
| `home_team` | string | Home team name. |
| `away_team` | string | Away team name. |
| `competition` | string | Competition or league name. |
| `kickoff_utc` | string | ISO8601 kickoff time, normalized to UTC (e.g. `2025-11-01T15:00:00+00:00`). |
| `odds_1x2` | object | Decimal odds for 1X2. Keys: `home`, `draw`, `away`; values must be > 0. |
| `status` | string | Match state: e.g. `scheduled`, `in_play`, `finished`. |

Fixtures are validated by `ingestion.fixtures.validator` (unique `match_id`, odds > 0, valid UTC kickoff).
