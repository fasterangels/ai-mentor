# v1.1 Roadmap

Summary of what is allowed in v1.1, what is out of scope, and how RFCs depend on each other.

---

## What is allowed in v1.1

- **RFC-001:** Expand activation scope (more matches per run, still capped). Config-only relaxation of ACTIVATION_MAX_MATCHES with a hard ceiling.
- **RFC-002:** Additional markets (beyond 1X2). Activation and guardrails extended to OU 2.5 and GG/NG via config (ACTIVATION_MARKETS).
- **RFC-003:** Live provider weighting / trust scoring. Rule-based, no ML; optional weights for parity and preference. Auditable and deterministic.
- **RFC-004:** Scheduler is **explicitly deferred** in v1.1. Scheduling remains external (cron, Task Scheduler, scripts). No in-process scheduler in v1.1.

All changes must preserve: kill-switch semantics, shadow-only behavior, existing guardrails, determinism, and explainability. No ML, no learned weights, no automatic policy changes beyond existing tuning (plan-tuning remains shadow-only and reversible).

---

## What is explicitly out of scope for v1.1

- **ML or learned models** for weighting, trust, or policy.
- **Automatic activation scope expansion** without explicit config.
- **Built-in scheduler** (see RFC-004 deferred).
- **New market types** not already supported by the analyzer.
- **Weakening of guardrails** or bypass of kill-switch.
- **Non-deterministic or non-explainable** decision paths.

---

## Dependency order between RFCs

1. **RFC-001 (Expand activation scope)** — No dependency on other RFCs. Can be implemented first. Independent of markets or provider weighting.
2. **RFC-002 (Additional markets)** — No dependency on RFC-001 or RFC-003. Can be implemented in parallel or after RFC-001. Requires policy and activation path to support per-market config (already partially there).
3. **RFC-003 (Provider weighting)** — No dependency on RFC-001 or RFC-002. Can be implemented in parallel. Affects compare/parity and optional preference only; does not block activation scope or markets.
4. **RFC-004 (Scheduler)** — Deferred. If revisited in a later version, it would depend only on existing ops/CLI (no dependency on 001–003).

Recommended implementation order for v1.1: **RFC-001 → RFC-002** (or in parallel), then **RFC-003** if desired. **RFC-004** not in v1.1.

---

## RFC index

| RFC | Title | Status |
|-----|--------|--------|
| [RFC-001](rfc/RFC-001-expand-activation-scope.md) | Expand activation scope (more matches, still capped) | Draft |
| [RFC-002](rfc/RFC-002-additional-markets.md) | Additional markets (beyond 1X2) | Draft |
| [RFC-003](rfc/RFC-003-live-provider-weighting.md) | Live provider weighting / trust scoring (NO ML) | Draft |
| [RFC-004](rfc/RFC-004-scheduler-deferred.md) | Scheduler (optional, explicitly deferred) | Draft (Deferred) |

Template: [RFC_TEMPLATE.md](rfc/RFC_TEMPLATE.md).
