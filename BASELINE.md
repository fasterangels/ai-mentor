# Baseline Lock (Step 0)

Stable, documented baseline of repo guarantees and CI expectations. No behavior change.

For canonical flow, disabled endpoints, safety gates, and verification details, see [STATUS.md](STATUS.md).

## How to run (copy-paste)

**Canonical flow (shadow / dry-run smoke):**
```bash
python -m pytest backend/tests/test_shadow_pipeline_e2e.py -q
```
Exits 0; exercises `/pipeline/shadow/run` path with in-memory DB.

**Tests:**
```bash
python -m pytest backend/tests/ -q
```
