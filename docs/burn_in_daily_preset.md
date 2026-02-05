# burn_in_daily ops preset

Use this preset for daily burn-in runs with activation enabled (single match, burn_in mode).

## Environment variables

| Variable | Value |
|----------|--------|
| `ACTIVATION_ENABLED` | `true` |
| `ACTIVATION_MODE` | `burn_in` |
| `ACTIVATION_MAX_MATCHES` | `1` |
| `LIVE_IO_ALLOWED` | `true` |
| `LIVE_WRITES_ALLOWED` | `true` |
| `ACTIVATION_KILL_SWITCH` | `false` |

## Command

```bash
ai-mentor ops burn-in-run --activation
```

Or with Python from repo root:

```bash
python tools/ops.py burn-in-run --activation
```

Optional: `--connector NAME`, `--output-dir reports`, `--dry-run` (no writes).

## Runner scripts

- **Unix:** `docs/burn_in_daily.sh` — sets the env vars above, runs the command once, exits non-zero if guardrails trigger critical alerts (status != ok or alerts_count > 0).
- **Windows:** `docs/burn_in_daily.ps1` — same behavior.
