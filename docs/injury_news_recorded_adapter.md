# Recorded injury/news adapter

Adapter key: `recorded_injury_news_v1`. Recorded-first; no network.

## Fixture path

- `backend/ingestion/fixtures/injury_news/` — JSON artifacts (see directory `README.md` for schema).

## Run in shadow mode

With injury/news enabled (persists to `injury_news_reports` and `injury_news_claims`):

```bash
set INJ_NEWS_ENABLED=1
python -m pytest backend/tests/test_shadow_pipeline_e2e.py -q
```

Or call `/api/v1/pipeline/shadow/run` with `INJ_NEWS_ENABLED=1`; the adapter runs before the main pipeline when the flag is set. Default: `INJ_NEWS_ENABLED` is off.
