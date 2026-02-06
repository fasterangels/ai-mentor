# Safety Flags (Defaults OFF)

## Core Safety
- **LIVE_IO_ALLOWED** = false (default)
- **LIVE_WRITES_ALLOWED** = false (default)
- **SNAPSHOT_WRITES_ALLOWED** = false (default)

## Shadow / Replay Modes
- **SNAPSHOT_REPLAY_ENABLED** = false (default)
- **INJ_NEWS_ENABLED** = false (default)
- **INJ_NEWS_SHADOW_ATTACH_ENABLED** = false (default)

## Notes
- All flags must be explicitly enabled to activate non-default behavior.
- Canonical supported flow remains: `/pipeline/shadow/run`
- `/api/v1/analyze` remains disabled (501 + hidden from OpenAPI)
