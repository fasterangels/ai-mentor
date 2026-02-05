# Sample recorded platform v2 fixture schema

Fixtures in this folder are JSON files consumed by `SampleRecordedPlatformV2Adapter`. Recorded only; no live network calls.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | string | Unique match identifier. |
| `home_team` | string | Home team name. |
| `away_team` | string | Away team name. |
| `competition` | string | Competition or league name. |
| `kickoff_utc` | string | ISO8601 kickoff time (UTC). |
| `odds_1x2` | object | Decimal odds: `home`, `draw`, `away`. |
| `status` | string | Match state: e.g. `scheduled`, `finished`. |

## Optional

- `venue`: string
