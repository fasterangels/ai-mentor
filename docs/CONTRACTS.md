# Pipeline Report Contracts

## Contract file locations
- Schema: backend/contracts/report.v1.schema.json
- Sample: backend/tests/fixtures/contracts/report.v1.sample.json

## Running contract tests

From repo root (after `pip install -r backend/requirements.txt`):

```bash
python -m pytest backend/tests/test_contract_report_schema.py -v
```

Test names (gate): `test_report_v1_sample_passes_schema`, `test_report_has_required_fields_snapshot_stability`, `test_pipeline_report_validates_against_report_v1_schema`.

## Schema version evolution (report.v1 → v2)

- **Additive first:** New optional fields/sections only; do not remove or rename required keys.
- **Breaking = new version:** Introduce `report.v2` and `report.v2.schema.json` for breaking changes; keep v1 supported during deprecation.
- **Deprecate then remove:** Document deprecation; after a period, stop emitting old version and optionally remove old schema.
