# RFC-002: Additional markets (beyond 1X2)

**Status:** Draft  
**Created:** 2025-02-01

---

## Context / Problem

v1.0 activation (e.g. burn-in) is 1X2-only by default. Operators may want to include Over/Under 2.5 or GG/NG (BTTS) in activation scope, with per-market policy and guardrails.

---

## Non-goals

- No new market types beyond those already supported by the analyzer (1X2, OU 2.5, GG/NG).
- No change to how markets are modeled in policy; only activation scope and config.
- No ML or adaptive logic for market selection.

---

## Proposed change

- Extend activation config to allow a list of markets (e.g. ACTIVATION_MARKETS=1X2,OU25,GGNG).
- Apply existing policy (min_confidence, dampening) per market; activation gate checks per market.
- Burn-in and live shadow compare/analyze already support multiple markets; ensure activation path respects the same guardrails per market.
- Document default (1X2-only) and safe expansion order (e.g. 1X2 first, then OU25, then GGNG).

---

## Safety & guardrails impact

- Per-market confidence and coverage must pass; no weakening of gates.
- Reports and index should record which markets were activated per run.
- Kill-switch and shadow-only behavior unchanged.

---

## Determinism / explainability impact

- Decisions remain deterministic per market; explainability unchanged.
- Order of market evaluation should be deterministic (e.g. fixed order 1X2, OU25, GGNG).

---

## Rollout plan

- Add ACTIVATION_MARKETS env (default 1X2); validate against allowed set.
- Roll out in docs first; then code change behind env. Recommend enabling one market at a time.
- No feature flag beyond env.

---

## Reversibility

- Set ACTIVATION_MARKETS back to 1X2 (or remove). No data migration; behavior reverts immediately.
