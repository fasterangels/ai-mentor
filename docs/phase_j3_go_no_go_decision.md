# Phase J3: Go/No-Go Decision

## Overview

The Go/No-Go decision is a **report-only** artifact derived from the J1 graduation result. It answers: “Given the current graduation outcome, is it a GO or NO_GO for proceeding to future planning?” It does **not** change production behavior, run pipelines automatically, or enforce any actions.

## What it is

- **Input:** `graduation_result.json` (from J1 graduation evaluation) in the provided reports directory.
- **Output:** Two deterministic artifacts in the same reports directory:
  - **go_no_go_decision.json** — Machine-readable: decision (GO | NO_GO), decision_time_utc, graduation_ref, failed_criteria, warnings.
  - **go_no_go_decision.md** — Human-readable: Decision, Timestamp, Reference to graduation result; if NO_GO, list of failed criteria with short details.
- **Logic:** PASS (overall) → GO; FAIL (overall) → NO_GO. Failed criteria and optional warnings are derived from the graduation result only.

## What it is NOT

- **No automation.** This mode produces decision reports only. It does not run the default pipeline, trigger deployments, or change any system behavior.
- **No default run.** Go/No-Go runs only when explicitly requested via `--mode go-no-go` (or `--ops go-no-go`).
- **Deterministic.** Same graduation result → same decision and artifact contents; filenames are fixed.

## How to run

- **CLI (from repo root):**  
  `python tools/operational_run.py --mode go-no-go --output-dir <path>`  
  Use `--output-dir` as the reports directory that contains (or will contain) `graduation_result.json`. Default is `reports` if omitted.

- **Backend entry (from backend dir):**  
  `python backend_entry.py --ops go-no-go`  
  Uses `REPORTS_DIR` environment variable (default `reports`) as the reports directory.

**Prerequisite:** Run J1 graduation evaluation first so that `graduation_result.json` exists in the reports directory. If the file is missing, the runner returns an error and does not write any decision artifacts.
