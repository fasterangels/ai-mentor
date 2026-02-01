# AI Mentor Local Application - Development Plan

## Architecture Overview
- **Frontend**: Vite + React (TypeScript) + Tailwind CSS + shadcn/ui → http://localhost:3000
- **Backend**: FastAPI + Uvicorn → http://127.0.0.1:8000
- **Local LLM**: Ollama → http://127.0.0.1:11434 (llama3:latest)
- **Database**: SQLite with single DatabaseManager
- **Language**: Greek UI with English code

## Backend Structure (FastAPI)
1. **main.py** - FastAPI app entry point, CORS, routes
2. **database.py** - Single DatabaseManager class, SQLite setup
3. **models.py** - SQLAlchemy models (Conversation, Message, Memory, Knowledge)
4. **ai_service.py** - Ollama integration, online fallback (ChatGPT API, web search)
5. **conversation_service.py** - Conversation CRUD operations
6. **memory_service.py** - User memory management with importance/tags
7. **knowledge_service.py** - Knowledge base management
8. **requirements.txt** - Python dependencies

## Frontend Structure (React + TypeScript)
1. **App.tsx** - Main app component with sidebar layout
2. **components/Sidebar.tsx** - Navigation sidebar (Συνομιλίες, Μνήμη, Γνώση, Εργαλεία, Ρυθμίσεις)
3. **components/ChatInterface.tsx** - Main chat UI with speech-to-text
4. **components/MessageList.tsx** - Display messages with thinking state indicators
5. **components/MessageInput.tsx** - Input with online toggle, speech button
6. **components/ConversationList.tsx** - List of conversations
7. **components/MemoryPanel.tsx** - User memory display/management
8. **components/KnowledgePanel.tsx** - Knowledge base display/management
9. **components/SettingsPanel.tsx** - Settings interface
10. **hooks/useOllama.ts** - Ollama connection status hook
11. **hooks/useSpeechRecognition.ts** - Browser speech-to-text (Greek)
12. **services/api.ts** - Backend API client
13. **types/index.ts** - TypeScript interfaces

## Windows Scripts
1. **start_windows.bat** - Start Ollama, backend, frontend, open browser
2. **stop_windows.bat** - Clean shutdown
3. **README.md** - Installation guide, shortcut creation instructions

## Key Features Implementation
- ✅ Multiple conversations with history
- ✅ "Σύνοψη μέχρι εδώ" button - structured summary
- ✅ "🌐 Online" toggle (default OFF) - one-time online access per message
- ✅ Thinking state indicator (🧠 Offline, 🌐 Online, 📚 Memory/Knowledge)
- ✅ User memory with importance/tags, user approval
- ✅ Knowledge base with title/summary/tags/date/sources
- ✅ Decision-making framework (structured output)
- ✅ Speech-to-text (Greek)
- ✅ Ollama status indicator

## Development Order
1. Backend setup (database, models, services)
2. Frontend setup (components, hooks, API integration)
3. Windows scripts
4. Testing & documentation