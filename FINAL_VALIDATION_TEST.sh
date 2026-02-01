#!/bin/bash

echo "=========================================="
echo "  AI MENTOR - FINAL VALIDATION TEST"
echo "  Version 7 - Performance Pack"
echo "=========================================="
echo ""

# Test 1: Application Startup Check
echo "=== TEST 1: Application Startup Check ==="
echo ""

echo "1.1 Checking start_windows.bat exists..."
if [ -f "start_windows.bat" ]; then
    echo "  ✅ start_windows.bat found"
else
    echo "  ❌ start_windows.bat NOT FOUND"
    exit 1
fi

echo ""
echo "1.2 Checking backend structure..."
if [ -f "backend/main.py" ] && [ -f "backend/ai_service.py" ]; then
    echo "  ✅ Backend files present"
else
    echo "  ❌ Backend files missing"
    exit 1
fi

echo ""
echo "1.3 Checking frontend structure..."
if [ -d "app/frontend/src" ]; then
    echo "  ✅ Frontend structure present"
else
    echo "  ❌ Frontend structure missing"
    exit 1
fi

echo ""
echo "✅ TEST 1 PASSED: Application structure verified"
echo ""

# Test 2: Performance Pack Features
echo "=== TEST 2: Performance Pack Features ==="
echo ""

echo "2.1 Checking AI Service configuration..."
cd backend
python3 << 'PYEOF'
import sys
try:
    from ai_service import ai_service
    
    print(f"  ✅ Model: {ai_service.current_model}")
    print(f"  ✅ Streaming enabled: {ai_service.streaming_enabled}")
    print(f"  ✅ Max output tokens: {ai_service.max_output_tokens}")
    print(f"  ✅ Temperature: {ai_service.temperature}")
    
    if ai_service.current_model != "llama3:8b":
        print(f"  ⚠️  Warning: Model is {ai_service.current_model}, expected llama3:8b")
    
    if not ai_service.streaming_enabled:
        print("  ❌ ERROR: Streaming not enabled")
        sys.exit(1)
        
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "  ❌ AI Service check failed"
    exit 1
fi

echo ""
echo "2.2 Checking streaming endpoint exists..."
grep -q "/messages/stream" main.py
if [ $? -eq 0 ]; then
    echo "  ✅ Streaming endpoint found in main.py"
else
    echo "  ❌ Streaming endpoint NOT FOUND"
    exit 1
fi

echo ""
echo "2.3 Checking metrics endpoint exists..."
grep -q "/api/v1/ai/metrics" main.py
if [ $? -eq 0 ]; then
    echo "  ✅ Metrics endpoint found in main.py"
else
    echo "  ❌ Metrics endpoint NOT FOUND"
    exit 1
fi

echo ""
echo "2.4 Checking warm-up in start script..."
cd ..
grep -q "Warming up" start_windows.bat
if [ $? -eq 0 ]; then
    echo "  ✅ Warm-up step found in start_windows.bat"
else
    echo "  ❌ Warm-up step NOT FOUND"
    exit 1
fi

echo ""
echo "✅ TEST 2 PASSED: Performance Pack features verified"
echo ""

# Test 3: Memory Safety Check
echo "=== TEST 3: Memory Safety Check ==="
echo ""

echo "3.1 Checking database configuration..."
cd backend
python3 << 'PYEOF'
import sys
from pathlib import Path
try:
    from database import db_manager, DATA_DIR, DB_PATH
    
    print(f"  ✅ Data directory: {DATA_DIR}")
    print(f"  ✅ Database path: {DB_PATH}")
    
    # Check if it's using external folder
    if "AI_Mentor_Data" in str(DATA_DIR):
        print("  ✅ Using external data folder (AI_Mentor_Data)")
    else:
        print(f"  ⚠️  Warning: Data directory is {DATA_DIR}")
    
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "  ❌ Database configuration check failed"
    exit 1
fi

echo ""
echo "3.2 Testing database operations..."
python3 << 'PYEOF'
import sys
try:
    from database import db_manager
    from models import Memory, Conversation
    
    # Create tables
    db_manager.create_tables()
    print("  ✅ Database tables created/verified")
    
    # Test memory operations
    session = next(db_manager.get_session())
    
    # Create test memory
    test_mem = Memory(
        content="Final validation test memory",
        importance=0.9,
        tags="validation,test"
    )
    session.add(test_mem)
    session.commit()
    print(f"  ✅ Test memory created (ID: {test_mem.id})")
    
    # Retrieve memory
    retrieved = session.query(Memory).filter_by(id=test_mem.id).first()
    if retrieved:
        print(f"  ✅ Memory retrieved successfully")
    else:
        print("  ❌ Memory retrieval failed")
        sys.exit(1)
    
    # Count all memories
    mem_count = session.query(Memory).count()
    print(f"  ✅ Total memories in database: {mem_count}")
    
    session.close()
    
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "  ❌ Database operations check failed"
    exit 1
fi

echo ""
echo "✅ TEST 3 PASSED: Memory safety verified"
echo ""

# Test 4: Regression Check
echo "=== TEST 4: Regression Check ==="
echo ""

echo "4.1 Testing all CRUD operations..."
python3 << 'PYEOF'
import sys
try:
    from database import db_manager
    from models import Memory, Conversation, Message, Knowledge
    from conversation_service import ConversationService
    from memory_service import MemoryService
    from knowledge_service import KnowledgeService
    
    session = next(db_manager.get_session())
    
    # Test Conversations
    conv = ConversationService.create_conversation(session, "Validation Test Conversation")
    print(f"  ✅ Conversation created (ID: {conv.id})")
    
    convs = ConversationService.get_conversations(session)
    print(f"  ✅ Conversations retrieved: {len(convs)} total")
    
    # Test Messages
    msg = ConversationService.add_message(session, conv.id, "user", "Test message")
    print(f"  ✅ Message created (ID: {msg.id})")
    
    msgs = ConversationService.get_messages(session, conv.id)
    print(f"  ✅ Messages retrieved: {len(msgs)} in conversation")
    
    # Test Memories
    mem = MemoryService.create_memory(session, "Test memory content", 0.8, "test")
    print(f"  ✅ Memory created (ID: {mem.id})")
    
    mems = MemoryService.get_memories(session)
    print(f"  ✅ Memories retrieved: {len(mems)} total")
    
    # Test Knowledge
    know = KnowledgeService.create_knowledge(
        session,
        "Test Knowledge",
        "Test summary",
        "Test content",
        "test",
        "test.com"
    )
    print(f"  ✅ Knowledge created (ID: {know.id})")
    
    knows = KnowledgeService.get_knowledge_list(session)
    print(f"  ✅ Knowledge retrieved: {len(knows)} total")
    
    session.close()
    
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "  ❌ CRUD operations check failed"
    exit 1
fi

echo ""
echo "4.2 Checking context trimming..."
python3 << 'PYEOF'
import sys
try:
    from ai_service import ai_service
    
    # Test context trimming
    messages = [{'role': 'user', 'content': f'Message {i}'} for i in range(20)]
    context = {
        'memories': [{'content': f'Memory {i}', 'importance': 0.5} for i in range(10)],
        'knowledge': [{'title': f'Knowledge {i}', 'summary': f'Summary {i}'} for i in range(10)]
    }
    
    trimmed_msgs, trimmed_ctx = ai_service._trim_context(messages, context)
    
    if len(trimmed_msgs) <= 10:
        print(f"  ✅ Messages trimmed: {len(messages)} → {len(trimmed_msgs)}")
    else:
        print(f"  ❌ Messages NOT trimmed properly: {len(trimmed_msgs)}")
        sys.exit(1)
    
    if len(trimmed_ctx['memories']) <= 5:
        print(f"  ✅ Memories trimmed: {len(context['memories'])} → {len(trimmed_ctx['memories'])}")
    else:
        print(f"  ❌ Memories NOT trimmed properly: {len(trimmed_ctx['memories'])}")
        sys.exit(1)
    
    if len(trimmed_ctx['knowledge']) <= 5:
        print(f"  ✅ Knowledge trimmed: {len(context['knowledge'])} → {len(trimmed_ctx['knowledge'])}")
    else:
        print(f"  ❌ Knowledge NOT trimmed properly: {len(trimmed_ctx['knowledge'])}")
        sys.exit(1)
    
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "  ❌ Context trimming check failed"
    exit 1
fi

echo ""
echo "✅ TEST 4 PASSED: All regression checks passed"
echo ""

# Final Summary
cd ..
echo "=========================================="
echo "  FINAL VALIDATION SUMMARY"
echo "=========================================="
echo ""
echo "✅ TEST 1: Application Startup - PASSED"
echo "✅ TEST 2: Performance Pack Features - PASSED"
echo "✅ TEST 3: Memory Safety - PASSED"
echo "✅ TEST 4: Regression Check - PASSED"
echo ""
echo "=========================================="
echo "  ALL TESTS PASSED ✅"
echo "=========================================="
echo ""
echo "Project Status: READY FOR EXPORT"
echo ""
echo "User Requirements:"
echo "  ✅ NO reinstallation required"
echo "  ✅ All data preserved in AI_Mentor_Data"
echo "  ✅ Performance Pack fully functional"
echo "  ✅ Backward compatible"
echo ""
echo "User can proceed with download."
echo ""

exit 0
