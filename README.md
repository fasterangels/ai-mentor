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