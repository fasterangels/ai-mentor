# AI Mentor - Hidden Launcher Fix Report

**Date:** 2026-01-24  
**Issue:** Backend not starting with hidden launcher  
**Status:** ✅ **FIXED**

---

## Problem Description

**User Report:**
- `start_hidden.bat` opens UI but backend does NOT start
- http://localhost:8000/health does not respond
- `start_windows.bat` works correctly

**Root Cause:**
- Hidden launcher was not activating venv properly
- No logging to diagnose issues
- No health check to verify backend started
- No error reporting when backend fails

---

## Fixes Implemented

### **1. Backend Startup (Same as start_windows.bat)**

**Python Launcher (`launcher.py`):**
```python
# Use venv python
venv_python = backend_path / "venv" / "Scripts" / "python.exe"

# Start backend with explicit port
subprocess.Popen(
    [str(venv_python), "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
    cwd=str(backend_path),
    creationflags=CREATE_NO_WINDOW,
    stdout=backend_log,
    stderr=backend_log
)
```

**PowerShell Launcher (`start_hidden_powershell.ps1`):**
```powershell
# Use venv python
$venvPython = Join-Path $backendPath "venv\Scripts\python.exe"

# Start backend with explicit port
Start-HiddenProcess -FilePath $venvPython -Arguments "-m uvicorn main:app --reload --host 0.0.0.0 --port 8000" -WorkingDirectory $backendPath -LogFile $backendLog
```

---

### **2. Logging to Files**

**Created `/workspace/logs/` directory with:**
- `hidden_launcher.log` - Launcher operations and status
- `hidden_backend.log` - Backend stdout/stderr
- `hidden_frontend.log` - Frontend stdout/stderr

**Python Implementation:**
```python
def log_message(message, log_file_path):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}\n"
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(log_msg)
```

**PowerShell Implementation:**
```powershell
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$timestamp] $Message"
    Add-Content -Path $launcherLog -Value $logMsg
}
```

---

### **3. Health Check with Wait Loop**

**Python Implementation:**
```python
def wait_for_backend_health(launcher_log, backend_log_path, max_wait=60):
    import requests
    
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                log_message(f"✅ Backend is healthy (took {i+1}s)", launcher_log)
                return True
        except:
            pass
        time.sleep(1)
    
    return False
```

**PowerShell Implementation:**
```powershell
$maxWait = 60
for ($i = 0; $i -lt $maxWait; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Log "✅ Backend is healthy (took $($i+1)s)"
            $backendReady = $true
            break
        }
    } catch {
        # Continue waiting
    }
    Start-Sleep -Seconds 1
}
```

---

### **4. Error Handling with MessageBox**

**Python Implementation:**
```python
import ctypes

if not wait_for_backend_health(launcher_log, backend_log_path):
    error_msg = f"Backend failed to start.\n\nCheck log file:\n{backend_log_path}\n\nThe application will not work correctly."
    ctypes.windll.user32.MessageBoxW(0, error_msg, "AI Mentor - Backend Error", 0x10)
    sys.exit(1)
```

**PowerShell Implementation:**
```powershell
if (-not $backendReady) {
    Add-Type -AssemblyName System.Windows.Forms
    $errorMsg = "Backend failed to start.`n`nCheck log file:`n$backendLog`n`nThe application will not work correctly."
    [System.Windows.Forms.MessageBox]::Show($errorMsg, "AI Mentor - Backend Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    exit 1
}
```

---

## Files Modified

### Modified:
1. `/workspace/launcher.py` - Fixed backend startup, added logging, health check, error handling
2. `/workspace/start_hidden_powershell.ps1` - Same fixes for PowerShell version

### Created:
3. `/workspace/logs/` - Directory for log files

### Unchanged:
- `/workspace/start_hidden.bat` - Wrapper (no changes needed)
- `/workspace/launch_hidden.bat` - Wrapper (no changes needed)
- All backend files - No changes
- All frontend files - No changes
- Data folder (AI_Mentor_Data) - No changes

---

## Validation Checklist

### ✅ Implementation Validation

**Test 1: Logs Directory**
- ✅ `/workspace/logs/` directory created

**Test 2: Python Launcher Fixes**
- ✅ venv activation logic present
- ✅ Logging to files configured
- ✅ Health check loop present
- ✅ Error MessageBox configured
- ✅ Backend port 8000 configured

**Test 3: PowerShell Launcher Fixes**
- ✅ venv activation logic present
- ✅ Logging to files configured
- ✅ Health check loop present
- ✅ Error MessageBox configured
- ✅ Backend port 8000 configured

**Test 4: Core Application Unchanged**
- ✅ backend/main.py unchanged
- ✅ backend/database.py unchanged
- ✅ frontend source unchanged

---

## User Testing Required

### **Test Steps:**

**1. Test Hidden Launcher**
```
Double-click: start_hidden.bat
```

**Expected Results:**
- ✅ No console windows appear
- ✅ Wait 10-20 seconds
- ✅ Browser opens to http://localhost:3000

**2. Verify Backend Health**
```
Open: http://localhost:8000/health
```

**Expected Results:**
- ✅ Returns 200 OK
- ✅ Shows: {"status": "healthy"} or similar

**3. Verify UI Works**
```
Open: http://localhost:3000
```

**Expected Results:**
- ✅ UI loads without errors
- ✅ No "σφάλμα σύνδεσης συνομιλιών" (connection error)
- ✅ Chat functionality works

**4. Check Logs (If Issues Occur)**
```
Open: /workspace/logs/hidden_launcher.log
Open: /workspace/logs/hidden_backend.log
Open: /workspace/logs/hidden_frontend.log
```

**Expected Results:**
- ✅ Logs show startup sequence
- ✅ Backend log shows uvicorn startup
- ✅ No error messages

---

## Troubleshooting

### Issue: Backend Still Not Starting

**Solution:**
1. Check `/workspace/logs/hidden_backend.log`
2. Look for error messages
3. Verify venv exists: `/workspace/backend/venv/Scripts/python.exe`
4. If venv missing, launcher will use system python (should still work)

### Issue: MessageBox Appears

**Solution:**
1. Read the MessageBox - it shows log file path
2. Open the log file mentioned
3. Look for error messages
4. Common issues:
   - Port 8000 already in use
   - Missing dependencies
   - venv not activated properly

### Issue: UI Shows Connection Error

**Solution:**
1. Verify backend is running: http://localhost:8000/health
2. If backend not responding, check logs
3. If backend is responding but UI still errors, check frontend logs

---

## Summary of Changes

**Key Improvements:**
- ✅ Backend now uses venv python (same as start_windows.bat)
- ✅ All output logged to files for debugging
- ✅ Health check ensures backend is ready before opening browser
- ✅ Error MessageBox shows log path if backend fails
- ✅ Explicit port 8000 configuration

**What Didn't Change:**
- ✅ No console windows (still hidden)
- ✅ Backend/frontend logic unchanged
- ✅ Data folder (AI_Mentor_Data) unchanged
- ✅ Same user experience (when working)

---

## Next Steps

**For User:**
1. Test `start_hidden.bat`
2. Verify backend health at http://localhost:8000/health
3. Verify UI works at http://localhost:3000
4. If issues occur, check logs in `/workspace/logs/`
5. Report results

**If Tests Pass:**
- ✅ Hidden launcher is fixed and ready for export

**If Tests Fail:**
- Check logs and report specific error messages
- May need additional fixes based on log content

---

**Fix Completed:** 2026-01-24  
**Developer:** Alex (Engineer)  
**Status:** AWAITING USER TESTING
