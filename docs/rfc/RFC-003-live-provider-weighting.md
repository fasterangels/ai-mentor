# RFC-003: Live provider weighting / trust scoring (NO ML)

**Status:** Draft  
**Created:** 2025-02-01

---

## Context / Problem

When multiple live providers (or live vs recorded) are used, operators may want to weight or score providers for consistency and parity—e.g. prefer one provider when odds differ, or flag low-trust segments. This must remain rule-based and explainable (no ML).

---

## Non-goals

- No ML models, no learned weights, no training data.
- No replacement of existing parity or compare logic; additive only.
- No automatic switching of providers based on learned behavior.

---

## Proposed change

- Introduce optional, rule-based “trust” or “weight” config per provider (e.g. static weights 0–1 or a small set of tiers).
- Use only for ordering or filtering in deterministic ways: e.g. when diffing live vs recorded, or when choosing which provider’s odds to prefer when both are available. All rules and thresholds explicit in config.
- Expose in reports (e.g. which provider was used for which decision, and why) for auditability.
- Document as explicitly non-ML: formula and inputs must be human-readable and static.

---

## Safety & guardrails impact

- No change to activation gates or kill-switch.
- Guardrails may use provider weight only as an input to existing checks (e.g. parity alerts). No new bypass of guardrails.
- All weighting logic auditable (config + logs/reports).

---

## Determinism / explainability impact

- Fully deterministic: same inputs and config always yield same weights and outcomes.
- Explainability: reports must state which provider/weight was used for each relevant decision.

---

## Rollout plan

- Add config schema and default (e.g. all providers weight 1.0). Optional feature; no behavior change until config is set.
- Document in runbook and system overview. Roll out behind env or config file.
- No feature flag beyond config presence.

---

## Reversibility

- Remove or reset weights to defaults. No data migration; behavior reverts immediately.
