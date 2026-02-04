# Release checklist v1

Use this checklist before tagging and releasing v1.x. All items must be green for a release.

---

## 1. Version and repo

- [ ] **VERSION file** at repo root exists and contains a single line matching semantic version (e.g. `1.0.0` or `1.0.1-alpha`). CI fails if missing or invalid.
- [ ] **CHANGELOG.md** has an entry for the release version (features/fixes list).

---

## 2. CI and tests

- [ ] **Mini-test suite** passes:
  ```bash
  pytest -q backend/tests/unit backend/tests/integration backend/tests/contract --maxfail=1
  ```
- [ ] **Contract lock** (analyze response critical keys): `pytest backend/tests/test_analyze_contract.py` (or contract tests in `backend/tests/contract`).
- [ ] **Windows E2E** (if applicable): canary preflight (GET /health, OPTIONS /api/v1/analyze) and full E2E job pass.
- [ ] **VERSION CI step** passes (workflow enforces VERSION present and semver pattern).
- [ ] **Reports gitignore** CI step passes (reports artifacts remain ignored).

---

## 3. Artifacts (Windows desktop release)

- [ ] **Backend exe** built (e.g. PyInstaller sidecar).
- [ ] **NSIS installer** produced when running full desktop build.
- [ ] **ci_build_stdout.txt**, **backend.log** present in packaging artifacts when E2E runs.

---

## 4. Docs freeze

- [ ] **docs/release_checklist_v1.md** (this file) and **docs/system_overview_v1.md** reviewed; no last-minute edits after checklist sign-off except version/date.
- [ ] **README** release section and install instructions match the version being released.

---

## 5. Tag and release

- [ ] Tag created (e.g. `v1.0.0`) pointing to the commit that passed the checklist.
- [ ] GitHub Release created from tag with release notes drawn from CHANGELOG.
- [ ] Installer (e.g. Windows setup exe) attached to the release if applicable.
