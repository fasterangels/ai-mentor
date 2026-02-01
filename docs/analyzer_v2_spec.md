# Analyzer v2 — Specification

**BLOCK 10 — Quality Gates, Decision Contract, Conflict Handling**

## Context

- **Existing system:** Resolver → Data Pipeline → Analyzer v1 → Evaluation.
- **Principles:** Offline-first, deterministic, evidence-based. Backend is authoritative; frontend is thin client.
- **Constraint:** v1 must not break. v2 is versioned and selectable via request or config.

---

## 1. Version selector

- **Request body:** Optional field `analyzer_version: "v1" | "v2"`.
- **Default:** `"v1"` (safe default; no change to current behaviour).
- **Override:** If `analyzer_version == "v2"`, the analysis flow uses the v2 analyzer; otherwise v1.
- **Config fallback (optional):** A server/config flag may force v2 for all requests; request-level override still takes precedence when present.

---

## 2. Decision contract (canonical)

Each market decision produced by v2 conforms to a stable schema (dict/DTO). All fields are defined; optionality is explicit.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | `str` | Yes | Market identifier, e.g. `"1X2"`, `"OU_2.5"`, `"BTTS"`. |
| `decision` | `str` enum | Yes | One of: `"PLAY"`, `"NO_BET"`, `"NO_PREDICTION"`. |
| `selection` | `str` | No | Only when `decision == "PLAY"`. See per-market vocabularies below. |
| `confidence` | `float` [0,1] | No | Only when `decision == "PLAY"`; optional for `NO_BET`. |
| `reasons` | `list[str]` | Yes | Short, audit-friendly reasons; **max 10** items. |
| `flags` | `list[str]` | Yes | From controlled vocabulary (see §3). Can be empty. |
| `evidence_refs` | `list[str]` | Yes | References into evidence pack IDs/keys. Can be empty but field exists. |
| `policy_version` | `str` | Yes | e.g. `"v2.0.0"`. |
| `meta` | `dict` | No | Safe extra structured info; no large blobs. |

### 2.1 Selection vocabularies (when `decision == "PLAY"`)

- **1X2:** `"HOME"` \| `"DRAW"` \| `"AWAY"`.
- **OU_2.5:** `"OVER"` \| `"UNDER"`.
- **BTTS:** `"YES"` \| `"NO"`.

If `decision != "PLAY"`, `selection` is omitted or `null`.

---

## 3. Flags vocabulary (controlled)

All flags are string literals from this set. Used in `decision.flags` and in global `analysis_run.flags`.

| Flag | Meaning |
|------|---------|
| `DATA_SPARSE` | Insufficient data points for reliable inference. |
| `SOURCE_CONFLICT` | Sources disagree above acceptable threshold; conflict score used. |
| `SIGNAL_CONTRADICTION` | Key signals contradict (e.g. one metric says OVER, another UNDER). |
| `LOW_QUALITY_EVIDENCE` | Evidence quality score below threshold. |
| `OUTLIER_DETECTED` | Outlier in input data; may affect confidence. |
| `SMALL_SAMPLE` | Sample size too small for market. |
| `STALE_DATA` | Data age exceeds policy limit. |
| `MISSING_KEY_FEATURES` | Evidence pack missing critical sections for this market. |
| `CONSENSUS_WEAK` | Consensus quality below soft threshold. |
| `MARKET_NOT_SUPPORTED` | Market requested but not supported in v2. |
| `INTERNAL_GUARDRAIL_TRIGGERED` | Internal safety/guardrail rule fired. |

Resolver-derived flags (mapped into analyzer output when resolver is not RESOLVED):

- `AMBIGUOUS` — resolver status AMBIGUOUS.
- `NOT_FOUND` — resolver status NOT_FOUND.

---

## 4. Quality gates (deterministic)

### 4.1 Hard gates → NO_PREDICTION

These force **NO_PREDICTION** (and appropriate flags) regardless of signal strength. Evaluated in order; first failure wins for that market or globally as specified.

| Gate | Condition | Result | Flags |
|------|-----------|--------|--------|
| Resolver not resolved | `resolver.status != "RESOLVED"` | All markets: NO_PREDICTION | Map status: AMBIGUOUS → `AMBIGUOUS`, NOT_FOUND → `NOT_FOUND`. |
| Missing evidence | Evidence pack missing critical sections required by market | That market: NO_PREDICTION | `MISSING_KEY_FEATURES` |
| Low evidence quality | Data quality score &lt; threshold (e.g. 0.5) | That market / global: NO_PREDICTION | `LOW_QUALITY_EVIDENCE` |
| Source conflict | Source conflict score ≥ T1 (block threshold) | That market: NO_PREDICTION | `SOURCE_CONFLICT` |
| Signal contradiction | Contradiction among key signals detected | That market: NO_PREDICTION | `SIGNAL_CONTRADICTION` |
| Market unsupported | Market not in v2 supported list | That market: NO_PREDICTION | `MARKET_NOT_SUPPORTED` |

### 4.2 Soft gates → NO_BET

Downgrade to **NO_BET** (no PLAY) when:

- **Borderline confidence:** Computed confidence in [min_confidence - delta, min_confidence] (e.g. just below threshold).
- **Too many minor warnings:** Count of non-hard-gate flags exceeds a limit (e.g. ≥ 2 minor flags).

Soft gates do not force NO_PREDICTION; they only prevent PLAY and set or retain NO_BET with relevant flags (e.g. `CONSENSUS_WEAK`, `SMALL_SAMPLE`).

---

## 5. Conflict handling policy

- **Inputs (from pipeline):**  
  - Per-feature or per-domain **consensus_quality** score in [0, 1].  
  - **Disagreement indicators:** e.g. number of sources, variance, or existing flags (e.g. `LOW_AGREEMENT`).

- **Thresholds:**  
  - **T1 (block):** If `consensus_quality < T1` → treat as hard gate: **NO_PREDICTION** + `SOURCE_CONFLICT` (or dedicated flag).  
  - **T2 (downgrade):** If `consensus_quality < T2` but ≥ T1 → allow only **NO_BET** unless confidence is exceptionally high (e.g. above a higher “override” confidence cap).

- **Policy summary:**  
  - `consensus_quality < T1` → block market (NO_PREDICTION).  
  - `T1 ≤ consensus_quality < T2` → NO_BET unless confidence &gt; override threshold.  
  - `consensus_quality ≥ T2` → normal gate logic (can yield PLAY if other gates pass).

Typical values (to be set in constants): e.g. T1 = 0.4, T2 = 0.65; override confidence e.g. 0.78.

---

## 6. Markets supported in v2 (initial set)

- **1X2**
- **OU_2.5**
- **BTTS**

Any other market requested is answered with one decision per market with `decision == "NO_PREDICTION"` and `flags` including `MARKET_NOT_SUPPORTED`.

---

## 7. Output structure

v2 **adds** structure; it does **not** remove existing API response fields. Existing top-level fields (`status`, `match_id`, `resolver`, `evidence_pack`, etc.) stay unchanged.

### 7.1 Analyzer block

- **analyzer** (object):
  - **status:** `"OK"` \| `"NO_PREDICTION"` (same semantics as v1).
  - **version:** `"v2"`.
  - **policy_version:** e.g. `"v2.0.0"`.
  - **analysis_run** (object):
    - **flags:** `list[str]` — global flags for the run.
    - **gate_results:** `list[{"gate_id": str, "pass": bool, "notes": str}]` — which gates were evaluated and result.
    - **conflict_summary:** optional object (e.g. per-market or global consensus_quality / conflict score) when available.
    - **counts:** e.g. `{"PLAY": n, "NO_BET": m, "NO_PREDICTION": k}` (decisions_by_kind).
  - **decisions:** `list` of decision objects conforming to the **Decision contract** (§2).

### 7.2 Backward compatibility

- v1 response shape is unchanged.
- When v2 is used, the same top-level keys are present; `analyzer` contains the extra v2 fields (`version`, `policy_version`, `analysis_run.gate_results`, `analysis_run.conflict_summary`, `analysis_run.counts`, and decisions with the new contract).
- Clients that ignore unknown fields remain compatible.

---

## 8. Implementation notes (pseudocode for a later block)

### 8.1 Extract features from evidence_pack

```
function extract_features(evidence_pack):
  features = {}
  for domain_name, domain_data in evidence_pack.domains:
    features[domain_name] = domain_data.data
    features[domain_name].quality_score = domain_data.quality.score
    features[domain_name].sources = domain_data.sources
    features[domain_name].flags = domain_data.quality.flags
  features.global_flags = evidence_pack.flags
  return features
```

### 8.2 Compute signal scores per market

```
function compute_signal_scores(features, market):
  if market == "1X2":
    # Derive HOME/DRAW/AWAY probabilities from features (e.g. team strength, H2H)
    return { HOME: p_h, DRAW: p_d, AWAY: p_a }, consensus_quality_1x2
  if market == "OU_2.5":
    # Derive OVER/UNDER from goals-related features
    return { OVER: p_o, UNDER: p_u }, consensus_quality_ou
  if market == "BTTS":
    # Derive YES/NO from goal expectancy
    return { YES: p_y, NO: p_n }, consensus_quality_btts
  return None, 0.0  # unsupported
```

### 8.3 Apply gates

```
function apply_gates(resolver_status, evidence_pack, market, scores, consensus_quality):
  gate_results = []
  # 1) Resolver
  if resolver_status != "RESOLVED":
    return NO_PREDICTION, [AMBIGUOUS|NOT_FOUND], gate_results + [gate(resolver, fail)]
  # 2) Missing key features for market
  if not has_required_sections(evidence_pack, market):
    return NO_PREDICTION, [MISSING_KEY_FEATURES], gate_results + [gate(missing_features, fail)]
  # 3) Low evidence quality
  if evidence_quality(evidence_pack) < THRESHOLD_QUALITY:
    return NO_PREDICTION, [LOW_QUALITY_EVIDENCE], gate_results + [gate(quality, fail)]
  # 4) Conflict
  if consensus_quality < T1:
    return NO_PREDICTION, [SOURCE_CONFLICT], gate_results + [gate(conflict, fail)]
  if consensus_quality < T2 and confidence <= OVERRIDE_CONFIDENCE:
    return NO_BET, [CONSENSUS_WEAK], gate_results + [gate(conflict_soft, fail)]
  # 5) Signal contradiction (e.g. one signal OVER, another UNDER)
  if has_signal_contradiction(scores, market):
    return NO_PREDICTION, [SIGNAL_CONTRADICTION], gate_results + [...]
  # 6) Market unsupported
  if market not in SUPPORTED_MARKETS_V2:
    return NO_PREDICTION, [MARKET_NOT_SUPPORTED], gate_results + [...]
  # 7) Soft gates: borderline confidence / too many minor flags
  if borderline_confidence(scores) or too_many_minor_flags(flags):
    return NO_BET, [existing flags], gate_results + [...]
  # 8) Otherwise compute PLAY selection and confidence
  return PLAY, selection, confidence, [], gate_results + [pass]
```

### 8.4 Emit decisions

```
function emit_decisions(per_market_results):
  decisions = []
  for market, (outcome, selection, confidence, flags, gate_results) in per_market_results:
    d = {
      market: market,
      decision: outcome,  # PLAY | NO_BET | NO_PREDICTION
      selection: selection if outcome == PLAY else None,
      confidence: confidence if outcome == PLAY else None,
      reasons: build_reasons(outcome, gate_results),
      flags: flags,
      evidence_refs: [],
      policy_version: POLICY_VERSION_V2,
      meta: {}
    }
    decisions.append(d)
  return decisions
```

---

## 9. Constants and types (Python)

Implementations use **backend/analyzer/v2/contracts.py** for:

- **DecisionKind:** `PLAY`, `NO_BET`, `NO_PREDICTION`.
- **Selection enums:** `Selection1X2` (HOME, DRAW, AWAY), `SelectionOU25` (OVER, UNDER), `SelectionBTTS` (YES, NO).
- **MarketFlag:** All controlled flags (e.g. `DATA_SPARSE`, `SOURCE_CONFLICT`, `MISSING_KEY_FEATURES`).
- **GateId:** Gate identifiers for `gate_results` (e.g. `resolver`, `evidence_quality`, `source_conflict`).
- **Thresholds:** `CONFLICT_T1_BLOCK`, `CONFLICT_T2_DOWNGRADE`, `OVERRIDE_CONFIDENCE_WHEN_BELOW_T2`, `THRESHOLD_EVIDENCE_QUALITY`, `MAX_MINOR_FLAGS_BEFORE_NO_BET`, `MAX_DECISION_REASONS`.
- **Version:** `ANALYZER_VERSION_V1`, `ANALYZER_VERSION_V2`, `ANALYZER_VERSION_DEFAULT`, `POLICY_VERSION_V2`, `SUPPORTED_MARKETS_V2`.

---

## 10. Acceptance (summary)

- Spec is implementable without guesswork: contract, flags, and gates are explicit.
- Flags and decision schema are consistent across the document and with `contracts.py`.
- v2 is deterministic and can always output NO_PREDICTION when gates fail.
- v1 remains the default; v2 is opt-in via `analyzer_version` (or config).
