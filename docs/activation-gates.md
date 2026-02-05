# Activation gates (controlled activation)

Activation is **not a current goal**. The system is designed for shadow and offline evaluation first.

If activation is ever used, it requires **manual approval** and explicit gates:

- **Manual approval token**: `ACTIVATION_APPROVAL_TOKEN` must be set in the environment and the same token must be provided in the run request/context (`approval_token`). No token, or a mismatch, denies activation.
- **Policy version pin**: The run must supply `policy_version_pin` equal to the current policy version (from the active policy). This prevents activating on a different policy than the one evaluated.
- **Prerequisites**:
  - Offline eval history: `offline_eval_runs` (from reports index) must be at least `MIN_OFFLINE_EVAL_RUNS` (env, default 365).
  - Audit trail: either explicitly enabled in context or activation runs already present in the index.
  - Policy history: policy repo directory or `POLICY_PATH` file must exist.

In addition, the **activation-allowed** gate requires:

- `ACTIVATION_ALLOWED` environment variable set to exactly `"true"` (default is off). This is separate from other activation-related env vars and is the master switch for the manual-approval gate.

On any failure, the gate raises `ActivationNotApprovedError` with code `ACTIVATION_NOT_APPROVED` and logs a guardrail trigger via ops events. No production behavior is changed to “active” by default; no live IO or writes are enabled.

**Shadow pipeline remains canonical.** The shadow pipeline and `/pipeline/shadow/run` are not impacted by this gate. The gate is only invoked by an explicit “activation runner” path that is not called by default.
