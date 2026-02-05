# Burn-in operational runbook

This runbook defines how to run and operate burn-in activation safely: required env, cadence, how to read reports, and what to do when alerts trigger.

---

## 1. Required environment flags

### Burn-in activation

- **ACTIVATION_ENABLED** = `true` — Master switch for activation; must be set for any activation (including burn-in).
- **ACTIVATION_MODE** = `burn_in` — Use burn-in mode (stricter than `limited`: caps 1–3 matches, higher confidence, real_provider/1X2 only by default).
- **LIVE_WRITES_ALLOWED** = `true` — Allows persisting resolutions and cache; required for burn-in activation.
- **LIVE_IO_ALLOWED** = `true` — Required for burn-in; live ingestion must be explicitly allowed.

Optional overrides (burn-in still caps/validates):

- **ACTIVATION_MAX_MATCHES** — Max matches per run; burn-in caps at 1–3 (default 1).
- **ACTIVATION_MIN_CONFIDENCE_BURN_IN** — Stricter confidence threshold (default 0.85).
- **ACTIVATION_CONNECTORS** — Comma list; burn-in default is `real_provider` only.
- **ACTIVATION_MARKETS** — Comma list; burn-in default is `1X2` only.

### Kill-switch (overrides everything)

- **ACTIVATION_KILL_SWITCH** = `true` — Forces shadow-only: no writes, no activation, regardless of other flags. Use for incidents or safe shutdown.

**Safe default for “observation only”:** Do not set `ACTIVATION_ENABLED` (or set it to `false`), or set **ACTIVATION_KILL_SWITCH** = `true`. Then all runs are shadow-only.

---

## 2. Recommended cadence and safe defaults

- **Daily cadence:** Run the burn-in ops pipeline once per day (e.g. after data refresh). Use a single consolidated command: `ai-mentor ops burn-in-run` (or `python tools/ops.py burn-in-run`).
- **Safe defaults:**  
  - Keep **ACTIVATION_KILL_SWITCH** = `true` until you have validated live_io, guardrails, and parity for several days.  
  - Use **ACTIVATION_MAX_MATCHES** = `1` for the first burn-in activations.  
  - Leave **ACTIVATION_ENABLED** = `false` (or unset) when you only want to collect reports and no writes.

---

## 3. How to interpret reports

### live_io_metrics

- **Counters:** `requests_total`, `failures_total`, `retries_total`, `timeouts_total`, etc.  
- **Latency:** `latency_ms.p50`, `latency_ms.p95`.  
- **Use:** Spot degradation (e.g. high failure rate or p95). Burn-in aborts activation if any critical live IO alert (max_live_io_alerts = 0).

### Guardrails (live shadow compare / analyze)

- **Identity mismatch:** Live vs recorded differ on teams/kickoff — investigate feed or mapping.
- **Missing markets / odds outliers / schema drift:** Coverage or data quality issues; fix before enabling activation.

### Parity reports (MULTI_PROVIDER_PARITY)

- **PARITY_* alerts:** Identity, missing markets, odds outliers between providers. Use to align feeds and thresholds; no automatic blocking.

### quality_audit

- **Reason effectiveness (decay), churn, calibration, stability:** Use for shadow tuning.  
- **Suggestions:** Dampening candidates and confidence band adjustments are suggestions only; do not change policy automatically.

---

## 4. Incident playbook

When alerts trigger (live_io, guardrails, or operational alerts):

1. **Disable activation immediately**  
   - Set **ACTIVATION_KILL_SWITCH** = `true`, or set **ACTIVATION_ENABLED** = `false`.  
   - Ensures all subsequent runs are shadow-only (no writes).

2. **Keep shadow-only mode**  
   - Continue running the same pipeline (e.g. `ops burn-in-run`) so that ingestion, live shadow compare, and live shadow analyze still run and produce reports, but no activation or persistence of decisions.

3. **Collect reports**  
   - Preserve the latest report bundle under `reports/burn_in/<run_id>/`.  
   - Preserve `reports/index.json` (and any referenced run summaries).  
   - Optionally run `ops health-check` and capture output for diagnostics.

4. **Triage**  
   - Use live_io_metrics, guardrails, parity, and quality_audit outputs to find root cause (connector, feed, policy, or config).  
   - Fix config or data; re-run in shadow-only until clean.  
   - Re-enable activation only after validation: clear **ACTIVATION_KILL_SWITCH** (or set to `false`) and set **ACTIVATION_ENABLED** = `true` when ready.

---

## 5. No scheduler

Burn-in ops are **not** scheduled by this system. Run the pipeline manually or via your own scheduler/cron using the CLI commands above.
