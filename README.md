# AI Mentor - Personal AI Assistant

An intelligent AI assistant with memory and knowledge management capabilities, powered by Ollama and built with FastAPI + React.

---

## Release v0.2.0 (Windows desktop)

**Install (Windows):**

1. Open the [Releases](https://github.com/fasterangels/ai-mentor/releases) page and download **AI-Mentor-Windows-setup.exe** for v0.2.0.
2. Run the installer (per-user, no admin required). The app and backend run via a Scheduled Task (`AI_Mentor_Backend`).
3. Launch **AI Μέντορας** from the Start Menu or desktop shortcut.

---

## v0.2.1 Hotfix (Stability Guardrails only)

**No new features.** This release contains CI/infra guardrails only:

- **Canary preflight:** Fail-fast job at start of Windows E2E (backend exe + GET /health + OPTIONS /api/v1/analyze with Origin).
- **Contract lock:** Pytest asserting analyze response critical keys (`resolver.status`, `analyzer.outcome` or `analyzer.decisions`, `match_id`).
- **Artifact invariants:** CI step asserting `ci_build_stdout.txt`, `backend.log`, and NSIS installer exist on success.
- **Rollback doc:** README section for deleting a release, moving/re-pushing a tag, re-running the release workflow.

**Install (Windows):** Download **AI-Mentor-Windows-setup.exe** for [v0.2.1](https://github.com/fasterangels/ai-mentor/releases) from Releases. Same installer flow as v0.2.0.

---

## Release v0.3.0 (Windows desktop)

**Highlights:**

- **Evaluation visibility (BLOCK 1):** Read-only KPIs (runtime, hash, stability, counts, flags) in the result view.
- **Result export (BLOCK 2):** Export current result as PDF/summary from the result header; print-friendly (debug hidden).
- **Settings surface (BLOCK 3):** Analyzer version (read-only), restore window on launch toggle, export file name template preview; localStorage only.
- **UX polish (BLOCK 4):** Tighter copy, aligned card headers/spacing, accessibility (aria-labels, focus order).

**Install (Windows):** Download **AI-Mentor-Windows-setup.exe** for [v0.3.0](https://github.com/fasterangels/ai-mentor/releases) from Releases. Same installer flow as v0.2.0.

---

## v0.3.1 Hotfix

**No new features. No UI or backend changes.** Stability hotfix only.

- Same installer flow as v0.3.0.
- **Install (Windows):** Download **AI-Mentor-Windows-setup.exe** for [v0.3.1](https://github.com/fasterangels/ai-mentor/releases) from Releases.

**Known limitations:**

- Windows only (NSIS installer).
- Backend must be running (started by installer/task); if the app shows "Backend starting…", wait a few seconds or restart the app.
- First analysis may take longer while the backend warms up.

### Rollback procedure (Windows release)

If you need to undo or redo a Windows release:

1. **Delete a release (GitHub)**  
   - Go to [Releases](https://github.com/fasterangels/ai-mentor/releases), open the release (e.g. v0.2.0), click **Delete this release**.  
   - This removes the release page and assets; the git tag remains unless you delete it.

2. **Move or re-push a tag**  
   - Delete the tag locally: `git tag -d v0.2.0`  
   - Delete the tag on the remote: `git push origin :refs/tags/v0.2.0`  
   - Re-tag the desired commit: `git tag -a v0.2.0 <commit> -m "Release v0.2.0"`  
   - Push the tag: `git push origin v0.2.0`  
   - Pushing a tag triggers the release workflow; ensure the tag points to the commit you want to build from.

3. **Re-run the release workflow**  
   - In GitHub: **Actions** → **release** → select the run for the tag → **Re-run all jobs**.  
   - Or push the same tag again after deleting it remotely (see step 2) so the workflow runs on the current commit the tag points to.

---

## 🚀 Quick Start

### **For Normal Use (Recommended)**

**Double-click:** `start_windows_hidden.vbs`

- ✅ Starts the application in the background
- ✅ No visible console windows
- ✅ Browser opens automatically
- ✅ Clean user experience

### **For Debugging**

**Double-click:** `start_windows.bat`

- ✅ Shows console windows for backend and frontend
- ✅ Displays startup logs and errors
- ✅ Useful for troubleshooting

---

## 📋 Prerequisites

Before running AI Mentor, ensure you have:

1. **Ollama** installed and running
   - Download: https://ollama.ai
   - Verify: Run `ollama list` in terminal

2. **Python 3.8+** installed
   - Download: https://www.python.org/downloads/

3. **Node.js 16+** and **pnpm** installed
   - Node.js: https://nodejs.org/
   - pnpm: `npm install -g pnpm`

4. **Required Python packages** (auto-installed on first run)
   - FastAPI, Uvicorn, SQLAlchemy, etc.

---

## 🎯 Features

### Core Capabilities
- **AI Chat Interface** - Conversational AI powered by Ollama
- **Memory System** - Remembers important information with importance scoring
- **Knowledge Base** - Store and retrieve structured knowledge
- **Context-Aware** - Uses memories and knowledge to provide relevant responses
- **Conversation Management** - Organize chats into separate conversations

### Performance Optimizations (Version 7)
- **Streaming Responses** - See AI responses as they're generated
- **Fast Model** - Uses llama3:8b for 2x faster responses
- **Context Trimming** - Optimized context size (60% reduction)
- **Model Warm-up** - Eliminates cold start delay
- **Performance Metrics** - Real-time latency and tokens/sec tracking

### Data Safety
- **External Data Folder** - All data stored in `%USERPROFILE%\AI_Mentor_Data`
- **Automatic Migration** - Seamlessly migrates from old database location
- **Backup-Friendly** - Single folder contains all user data

---

## 🖥️ System Requirements

- **OS:** Windows 11 (or Windows 10)
- **RAM:** 8GB minimum (16GB recommended for larger models)
- **Disk:** 10GB free space (for Ollama models)
- **Network:** Internet connection for initial setup

---

## 📂 Project Structure

```
AI_Mentor/
├── start_windows_hidden.vbs    # Hidden launcher (recommended)
├── start_windows.bat            # Visible launcher (debugging)
├── backend/                     # FastAPI backend
│   ├── main.py                 # API endpoints
│   ├── ai_service.py           # Ollama integration
│   ├── database.py             # Database management
│   ├── models.py               # Data models
│   └── *_service.py            # Business logic
├── app/frontend/               # React frontend
│   ├── src/
│   │   ├── components/         # UI components
│   │   └── services/           # API client
│   └── package.json
└── README.md                   # This file
```

---

## 🔧 Configuration (Optional)

Create `backend/.env` file for custom settings:

```bash
# Model Configuration
OLLAMA_MODEL=llama3:8b          # Default model (fast)
OLLAMA_URL=http://localhost:11434

# Performance Tuning
STREAMING_ENABLED=true          # Enable streaming responses
MAX_OUTPUT_TOKENS=512           # Max tokens per response
TEMPERATURE=0.7                 # Response randomness (0-1)
TOP_P=0.9                       # Nucleus sampling threshold

# Data Directory (optional override)
# DATA_DIR=D:\MyCustomPath\AI_Mentor_Data

# OpenAI API Key (optional, for online mode)
# OPENAI_API_KEY=your-api-key-here
```

---

## Live shadow compare (LIVE_SHADOW_COMPARE)

**LIVE_SHADOW_COMPARE** is a run mode that compares live ingestion to recorded fixtures (normalization only, no decisions, no writes by default).

### Behavior

- **No analyzer:** The pipeline runs normalization only; no picks or decisions are produced.
- **No writes by default:** Report and index updates are written only if `LIVE_WRITES_ALLOWED=true` (default: false). Cache and DB writes are hard-blocked in this mode unless that flag is set.

### How to run safely

1. **Required env (for live path):**  
   - `LIVE_IO_ALLOWED=true`  
   - For **real_provider**: `REAL_PROVIDER_LIVE=true`, `REAL_PROVIDER_BASE_URL`, `REAL_PROVIDER_API_KEY`
2. **Optional:** `LIVE_WRITES_ALLOWED=true` to persist the compare report and append its summary to `reports/index.json`.
3. **API:**  
   - `POST /api/v1/reports/live-shadow/run` with body `{"connector_name": "real_provider"}` (or another connector that supports live + recorded).  
   - `GET /api/v1/reports/live-shadow/latest` returns the latest compare summary from `reports/index.json` (read-only, no DB).

Reports are stored under `reports/live_shadow_compare/<run_id>.json`; the index is updated only when writes are allowed.

---

### Multi-provider parity mode (MULTI_PROVIDER_PARITY)

**MULTI_PROVIDER_PARITY** compares the same match set from two providers (e.g. `sample_platform` and `real_provider_2`) using recorded fixtures by default. No live calls in tests.

**How to run**

- From code: call `run_provider_parity(provider_a_name="sample_platform", provider_b_name="real_provider_2", ...)` from `runner.provider_parity_runner`.
- Optional `match_ids` limits the set; if omitted, the union of both providers’ match lists is used.
- Reports are written to `reports/provider_parity/<run_id>.json` and a summary is appended to `reports/index.json` under `provider_parity_runs` / `latest_provider_parity_run_id`.

**How to interpret alerts**

- **PARITY_IDENTITY_MISMATCH:** Number of matches where identity (teams, kickoff) differs between providers exceeds `max_identity_mismatch_count`. Indicates possible feed or mapping issues.
- **PARITY_MISSING_MARKETS_PCT:** Percentage of expected 1X2 markets missing on one provider exceeds `max_missing_markets_pct`. Indicates coverage gaps.
- **PARITY_ODDS_OUTLIERS:** Number of odds with drift above threshold (pct or abs) exceeds `max_odds_outlier_count`. Indicates pricing or timing drift.

Alerts are **shadow-only** (no blocking); use them to triage and fix data or config.

---

### Decision quality audit (quality-audit)

The **quality-audit** CLI produces deep-audit reports from stored snapshots and resolutions: reason effectiveness over time (with configurable decay), reason churn, confidence calibration by band per market, and stability (pick flip rate, confidence volatility). Use these for **shadow tuning** only; suggestions do not change policy automatically.

**How to run**

- From repo root: `python tools/quality_audit.py [--last-n N] [--date-from ISO] [--date-to ISO] [--output-dir reports]`
- Requires DB with analysis_runs, snapshot_resolutions, and predictions (e.g. after shadow/analyze runs).
- Output: `reports/quality_audit/<run_id>.json` and an entry in `reports/index.json` under `quality_audit_runs` / `latest_quality_audit_run_id`.

**How to use the outputs**

- **reason_effectiveness_over_time:** Per-reason win/loss/neutral and decay-weighted contribution. Use to spot reasons whose effectiveness degrades (see suggestions).
- **reason_churn:** Appearance/disappearance of reason codes across runs; high churn may indicate instability.
- **confidence_calibration:** Per market and band, predicted confidence vs empirical accuracy. Use to tune bands or thresholds.
- **stability:** Pick flip rate and confidence volatility (p95 delta) across comparable snapshots.
- **suggestions:** Dampening candidates (reasons to consider down-weighting) and confidence band adjustments. These are **suggestions only**; no automatic policy change.

### Burn-in ops (stabilization, no scheduler)

See **docs/runbook_burnin.md** for required env, cadence, and incident playbook.

- **Single pipeline:** `python tools/ops.py burn-in-run [--connector NAME] [--dry-run] [--activation]`  
  Runs: ingestion → live shadow compare → live shadow analyze → (optional) burn-in activation if gates pass. Writes one report bundle under `reports/burn_in/<run_id>/` and updates `reports/index.json` (status, alerts, activated, counts). Use `--dry-run` to skip writing bundle/index. Retention: configurable max bundles (default 30); pruning is deterministic and logged in index.
- **Health check:** `python tools/ops.py health-check`  
  Validates readiness, required tables, connector availability, policy presence. Exit code nonzero on failure.

---

### v1.0 Burn-in Operations

**Daily run (preset burn_in_daily)**  
Use the preset to run burn-in with activation enabled (one match, burn_in mode):

- **Runner script (Unix):** `./docs/burn_in_daily.sh` — sets env (ACTIVATION_ENABLED=true, ACTIVATION_MODE=burn_in, ACTIVATION_MAX_MATCHES=1, LIVE_IO_ALLOWED=true, LIVE_WRITES_ALLOWED=true, ACTIVATION_KILL_SWITCH=false), runs `ai-mentor ops burn-in-run --activation` once, **exits non-zero if guardrails trigger critical alerts** (status != ok or alerts_count > 0).
- **Runner script (Windows):** `.\docs\burn_in_daily.ps1` — same behavior.
- Preset details: **docs/burn_in_daily_preset.md**.

**What “normal” looks like**  
- Status `ok`, alerts_count `0`, activated `true` or `false` depending on gates. Matches count and connector name in the last line of output (or in the daily summary).

**When to flip the kill-switch**  
- Set **ACTIVATION_KILL_SWITCH=true** (or **ACTIVATION_ENABLED=false**) immediately if alerts spike, live IO degrades, or you need to stop activation for any reason. All runs then become shadow-only (no writes, no activation). See **docs/runbook_burnin.md** incident playbook.

**Daily summary**  
- After a run, print a concise summary of the latest burn-in bundle (alerts, activated count, latency/confidence when available):  
  `python tools/burn_in_summary.py [--reports-dir reports]`  
  No persistence changes; reads `reports/index.json` and `reports/burn_in/<latest_run_id>/`.

---

## 📊 Performance Metrics

Access real-time performance data:
- **Metrics API:** http://localhost:8000/api/v1/ai/metrics
- **Health Check:** http://localhost:8000/health

**Expected Performance:**
- First message: ~1-2s (with warm-up)
- Subsequent messages: ~1-2s
- Context size: 60% smaller than previous versions
- Streaming: Immediate token display

---

## 🗂️ Data Folder & Backups

### Data Location
All user data is stored in: `%USERPROFILE%\AI_Mentor_Data\`

**Contents:**
- `ai_mentor.db` - SQLite database with all conversations, memories, and knowledge

### Backup Strategy
**To backup your data:**
1. Close AI Mentor application
2. Copy the entire `AI_Mentor_Data` folder
3. Store in a safe location (external drive, cloud storage, etc.)

**To restore from backup:**
1. Close AI Mentor application
2. Replace `%USERPROFILE%\AI_Mentor_Data\` with your backup folder
3. Restart AI Mentor

### Moving Data to Another Computer
1. Copy `AI_Mentor_Data` folder from old computer
2. On new computer, place it in `%USERPROFILE%\AI_Mentor_Data\`
3. Install AI Mentor and run normally

---

## 🛠️ Troubleshooting

### Application Won't Start

**Check Ollama:**
```bash
ollama list
```
If not running: `ollama serve`

**Check Python:**
```bash
python --version
```
Should be 3.8 or higher

**Check Node.js:**
```bash
node --version
pnpm --version
```

### Console Windows Appear (When Using Hidden Launcher)

If you see console windows when using `start_windows_hidden.vbs`:
1. Right-click the file → Properties
2. Ensure it opens with "Microsoft Windows Based Script Host"
3. Try running as Administrator

**Alternative:** Use PowerShell hidden launcher:
```powershell
Start-Process -FilePath "start_windows.bat" -WindowStyle Hidden
```

### Slow Responses

**Install faster model:**
```bash
ollama pull llama3:8b
```

**Check metrics:**
- Open http://localhost:8000/api/v1/ai/metrics
- Verify `model: llama3:8b` and `streaming_enabled: true`

### Database Issues

**Reset database (WARNING: Deletes all data):**
1. Close AI Mentor
2. Delete `%USERPROFILE%\AI_Mentor_Data\ai_mentor.db`
3. Restart AI Mentor (new database will be created)

**Backup first!**

### Port Already in Use

If ports 8000 or 3000 are busy:
1. Close other applications using these ports
2. Or modify ports in:
   - Backend: `backend/main.py` (line: `uvicorn.run(..., port=8000)`)
   - Frontend: `app/frontend/vite.config.ts`

---

## API Contract
See `docs/api-surface.md`. Do not use `/api/v1/analyze`; use `/pipeline/shadow/run`.

---

## 🔍 API Documentation

Once running, access interactive API docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

**Key Endpoints:**
- `GET /health` - System health check
- `GET /api/v1/ai/status` - Ollama connection status
- `GET /api/v1/ai/metrics` - Performance metrics
- `POST /messages` - Send message (non-streaming)
- `POST /messages/stream` - Send message (streaming)
- `GET /conversations` - List conversations

### Reports viewer (read-only)

The backend exposes a **read-only reports API** to inspect `reports/index.json` and individual report files (e.g. burn-in bundles, tuning plans) without writing anything.

**How to run and query:**

1. **Reports directory**  
   By default the API serves from the `reports/` directory (relative to the process working directory). Override with env:  
   `REPORTS_DIR=/path/to/reports`

2. **Endpoints**
   - `GET /api/v1/reports/index` — returns the full `reports/index.json`.
   - `GET /api/v1/reports/item/{run_id}` — returns which index lists contain that `run_id`, their entry, and relative paths to report files (e.g. `burn_in/<run_id>/summary.json`).
   - `GET /api/v1/reports/file?path=<relative>` — serves a single report JSON file. `path` must be relative and under `reports/` (path traversal is blocked).

3. **Optional auth**
   - If you set `REPORTS_READ_TOKEN` in the environment, the API requires the header `X-Reports-Token: <value>` to match.  
   - If `REPORTS_READ_TOKEN` is not set, no token is required (suitable for local use).

**Example (no token):**
```bash
curl http://localhost:8000/api/v1/reports/index
curl "http://localhost:8000/api/v1/reports/file?path=burn_in/my_run_id/summary.json"
```

**Example (with token):**
```bash
export REPORTS_READ_TOKEN=my-secret
curl -H "X-Reports-Token: my-secret" http://localhost:8000/api/v1/reports/index
```
- `GET /memories` - List memories
- `GET /knowledge` - List knowledge entries

---

## 📚 Additional Resources

### Documentation
- **Performance Pack Report:** `PERFORMANCE_PACK_REPORT.md`
- **Validation Report:** `FINAL_VALIDATION_REPORT.md`
- **Data Folder Guide:** `DATA_FOLDER_MIGRATION_GUIDE.md`

### Support
- **Ollama Documentation:** https://ollama.ai/docs
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **React Documentation:** https://react.dev/

---

## 🎉 Version History

### Version 7 - Performance Pack (Current)
- ✅ Streaming responses (SSE)
- ✅ llama3:8b default model (2x faster)
- ✅ Context trimming (60% reduction)
- ✅ Model warm-up on startup
- ✅ Performance metrics API
- ✅ Hidden launcher for clean UX

### Version 6 - Data Folder Architecture
- ✅ External data folder (`AI_Mentor_Data`)
- ✅ Automatic database migration
- ✅ Backup-friendly structure

### Earlier Versions
- Basic chat functionality
- Memory and knowledge systems
- Conversation management

---

## 📝 License

This project is for personal use. Modify and distribute as needed.

---

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

**Enjoy your AI Mentor! 🚀**

For questions or issues, check the troubleshooting section above or review the validation reports in the project folder.