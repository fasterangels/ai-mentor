# Evidence Schema v1 (Injuries / News)

## Purpose

Normalized, versioned, offline-first schema for time-sensitive evidence items:

- **Injuries** – player availability
- **Suspensions** – disciplinary
- **Team news** – tactical/lineup-related
- **Disruptions** – e.g. travel issues (news-like evidence)

Used for storage and future analysis only. **No decision logic or ML** uses this data yet.

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| evidence_id | string (UUID) | yes | Unique id |
| fixture_id | string | yes | Match/fixture identifier |
| team_id | string | no | Team (nullable for fixture-level) |
| player_id | string | no | Player (for injury/suspension when available) |
| evidence_type | enum | yes | INJURY, SUSPENSION, TEAM_NEWS, DISRUPTION |
| title | string | yes | Short title (max 256) |
| description | string | no | Optional, max 2000 |
| source_class | enum | yes | RECORDED, LIVE_SHADOW, EDITORIAL, UNKNOWN |
| source_name | string | yes | Source identifier |
| source_ref | string | no | Optional external ref |
| reliability_tier | enum | yes | HIGH, MED, LOW |
| observed_at | datetime (UTC) | yes | When observed |
| effective_from | datetime | no | Defaults to observed_at in builder |
| expected_valid_until | datetime | no | Optional validity end |
| created_at | datetime | yes | Record creation time |
| checksum | string | yes | SHA-256 of canonicalized content |
| conflict_group_id | string | no | For future conflict handling |
| tags | list of strings | no | Optional tags (JSON) |

## Checksum canonicalization

- Fields that define “content” are serialized to a JSON object with **sorted keys**.
- No `evidence_id` or volatile timestamps in the canonical payload (observed_at/created_at/effective_from/expected_valid_until are included for content identity).
- Same logical content → same checksum. Used for deduping and audit.

## Recorded input (JSON)

```json
{
  "fixture_id": "match_001",
  "items": [
    {
      "title": "...",
      "evidence_type": "INJURY",
      "source_class": "RECORDED",
      "source_name": "recorded_fixture",
      "reliability_tier": "HIGH",
      "observed_at": "2025-01-15T10:00:00+00:00"
    }
  ]
}
```

Required per item: `title`, `evidence_type`, `source_class`, `source_name`, `reliability_tier`, `observed_at`.

## What is NOT implemented yet

- No decay modeling
- No use in analyzer or decision logic
- No conflict resolution (only conflict/merge markers stored)
- No live fetch; recorded/stub ingestion only
