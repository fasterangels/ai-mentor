# RFC-001: Expand activation scope (more matches, still capped)

**Status:** Draft  
**Created:** 2025-02-01

---

## Context / Problem

v1.0 burn-in caps activation at 1 match (configurable 1–3 via ACTIVATION_MAX_MATCHES). Operators may want to safely expand the number of matches per run while remaining within a hard cap and existing guardrails.

---

## Non-goals

- No change to kill-switch or shadow-only semantics.
- No automatic scaling; caps remain explicit and configurable.
- No new markets or providers in this RFC.

---

## Proposed change

- Allow ACTIVATION_MAX_MATCHES to be raised (e.g. 5–10) with a documented global cap (e.g. 10).
- Keep burn_in mode logic; only relax the per-run match cap when explicitly configured.
- Document the cap in runbook and system overview; enforce in code with a ceiling constant.

---

## Safety & guardrails impact

- Existing guardrails (live IO alerts, identity mismatch, confidence gate) unchanged.
- More matches per run increases blast radius if a bad run occurs; cap limits exposure.
- Audit trail (reports, index) already records matches_count; no new audit surface.

---

## Determinism / explainability impact

- No change to decision logic or explainability. Same policy and reasons per match.
- Order of match processing should remain deterministic (e.g. sorted match_ids).

---

## Rollout plan

- Add ceiling constant (e.g. MAX_ACTIVATION_MATCHES = 10); ship behind existing ACTIVATION_MAX_MATCHES env.
- Document in runbook; operators opt in by setting ACTIVATION_MAX_MATCHES higher (up to cap).
- No feature flag beyond existing activation env vars.

---

## Reversibility

- Set ACTIVATION_MAX_MATCHES back to 1 (or 3). No data migration; behavior reverts immediately.
