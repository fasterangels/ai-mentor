# Stub Platform Fixtures

Parity fixtures for stub_platform connector (served via HTTP stub server).

These fixtures match the structure of `sample_platform` fixtures but are served via the local stub HTTP server to test live IO connectors.

## Schema

Each fixture JSON file must contain:
- `match_id` (or `id`): unique match identifier
- `home_team`: home team name (string)
- `away_team`: away team name (string)
- `competition`: competition name (string)
- `kickoff_utc`: ISO8601 UTC timestamp (string)
- `odds_1x2`: object with `home`, `draw`, `away` (decimal odds, numbers > 0)
- `status`: match status (e.g., "scheduled", "in_play", "finished")

## Usage

The stub server (`ingestion/stub_server.py`) serves these fixtures via:
- `GET /matches` - list all matches
- `GET /matches/{match_id}` - get specific match

The stub connector (`ingestion/connectors/stub_platform.py`) fetches from the stub server and requires `LIVE_IO_ALLOWED=true`.
