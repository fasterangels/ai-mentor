#!/usr/bin/env bash
# burn_in_daily runner: set preset env, run ops burn-in-run once, exit non-zero if critical alerts.
# Usage: from repo root, ./docs/burn_in_daily.sh   or   bash docs/burn_in_daily.sh
set -e
export ACTIVATION_ENABLED=true
export ACTIVATION_MODE=burn_in
export ACTIVATION_MAX_MATCHES=1
export LIVE_IO_ALLOWED=true
export LIVE_WRITES_ALLOWED=true
export ACTIVATION_KILL_SWITCH=false

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPS_PY="$REPO_ROOT/tools/ops.py"
if [ ! -f "$OPS_PY" ]; then
  echo "ERROR: tools/ops.py not found. Run from repo root." >&2
  exit 2
fi

LAST_LINE=$(python "$OPS_PY" burn-in-run --activation 2>&1 | tail -n1)
# Format: run_id,status,alerts_count,activated,bundle_dir
STATUS=$(echo "$LAST_LINE" | cut -d, -f2)
ALERTS=$(echo "$LAST_LINE" | cut -d, -f3)
if [ "$STATUS" != "ok" ] || [ "${ALERTS:-0}" -gt 0 ]; then
  exit 1
fi
exit 0
