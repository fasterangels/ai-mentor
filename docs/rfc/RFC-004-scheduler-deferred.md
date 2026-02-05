# RFC-004: Scheduler (optional, explicitly deferred)

**Status:** Draft (Deferred)  
**Created:** 2025-02-01

---

## Context / Problem

v1.0 has no built-in scheduler; burn-in and ops are run manually or via external cron/task runner. Operators may want an optional in-process or sidecar scheduler to run burn_in_daily (or other presets) on a cadence.

---

## Non-goals

- Not committing to implementing a scheduler in v1.1. This RFC records the option and defers it.
- No change to burn-in or ops semantics; scheduler would only invoke existing commands.
- No new activation or guardrail logic in this RFC.

---

## Proposed change

- **Deferred:** No implementation in v1.1. Document that scheduling remains external (cron, Task Scheduler, systemd timer, or wrapper script).
- If implemented later: scheduler would run existing CLI/ops commands (e.g. burn_in_daily script) on a configurable schedule; no new code paths for activation or guardrails.
- Any future scheduler must: (1) use same env and presets as manual runs, (2) respect kill-switch and ACTIVATION_* flags, (3) not persist schedule state in a way that bypasses audit.

---

## Safety & guardrails impact

- N/A for v1.1 (deferred). Future scheduler must not weaken guardrails; it would only trigger existing, already-guarded flows.

---

## Determinism / explainability impact

- N/A for v1.1. Future scheduler would not change determinism of the underlying ops runs.

---

## Rollout plan

- No rollout in v1.1. If revisited: add optional scheduler module or sidecar; document schedule config and audit; rollout behind feature flag or explicit opt-in.

---

## Reversibility

- N/A (deferred). If a scheduler is added later, disabling it would be via config or feature flag; no impact on manual runs.
