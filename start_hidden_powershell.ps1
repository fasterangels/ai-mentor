# AI Mentor - PowerShell Hidden Launcher
# Fixed version with proper backend startup, logging, and health checks

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create logs directory
$logsDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# Log file paths
$launcherLog = Join-Path $logsDir "hidden_launcher.log"
$backendLog = Join-Path $logsDir "hidden_backend.log"
$frontendLog = Join-Path $logsDir "hidden_frontend.log"

# Function to log messages
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$timestamp] $Message"
    Write-Host $logMsg
    Add-Content -Path $launcherLog -Value $logMsg
}

# Function to start process hidden with logging
function Start-HiddenProcess {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogFile
    )
    
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    
    $process = [System.Diagnostics.Process]::Start($psi)
    
    # Redirect output to log file
    if ($LogFile) {
        $outputJob = Start-Job -ScriptBlock {
            param($proc, $log)
            while (-not $proc.HasExited) {
                $line = $proc.StandardOutput.ReadLine()
                if ($line) {
                    Add-Content -Path $log -Value $line
                }
            }
        } -ArgumentList $process, $LogFile
        
        $errorJob = Start-Job -ScriptBlock {
            param($proc, $log)
            while (-not $proc.HasExited) {
                $line = $proc.StandardError.ReadLine()
                if ($line) {
                    Add-Content -Path $log -Value $line
                }
            }
        } -ArgumentList $process, $LogFile
    }
    
    return $process
}

Write-Log "=================================================="
Write-Log "  AI MENTOR - HIDDEN LAUNCHER"
Write-Log "=================================================="
Write-Log ""

# Step 1: Check Ollama
Write-Log "Step 1: Checking Ollama..."
try {
    $ollamaCheck = Start-Process -FilePath "ollama" -ArgumentList "list" -WindowStyle Hidden -PassThru -Wait
    if ($ollamaCheck.ExitCode -eq 0) {
        Write-Log "✅ Ollama is running"
    }
} catch {
    Write-Log "⚠️  Starting Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# Step 2: Warm up Ollama
Write-Log ""
Write-Log "Step 2: Warming up Ollama model..."
try {
    Start-Process -FilePath "ollama" -ArgumentList "run llama3:8b Hello" -WindowStyle Hidden -Wait
    Write-Log "✅ Ollama warm-up complete"
} catch {
    Write-Log "⚠️  Ollama warm-up failed"
}

# Step 3: Start Backend with venv
Write-Log ""
Write-Log "Step 3: Starting backend..."
$backendPath = Join-Path $scriptDir "backend"
$venvPython = Join-Path $backendPath "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Log "❌ venv python not found at: $venvPython"
    Write-Log "Using system python instead"
    $venvPython = "python"
}

Write-Log "Starting backend with: $venvPython"
Write-Log "Backend log: $backendLog"

# Clear backend log
"" | Out-File -FilePath $backendLog

$backendProcess = Start-HiddenProcess -FilePath $venvPython -Arguments "-m uvicorn main:app --reload --host 0.0.0.0 --port 8000" -WorkingDirectory $backendPath -LogFile $backendLog
Write-Log "✅ Backend started (PID: $($backendProcess.Id))"

# Step 4: Wait for backend health check
Write-Log ""
Write-Log "Step 4: Waiting for backend to be ready..."

$maxWait = 60
$backendReady = $false

for ($i = 0; $i -lt $maxWait; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Log "✅ Backend is healthy (took $($i+1)s)"
            $backendReady = $true
            break
        }
    } catch {
        if ($i -eq 0) {
            Write-Log "Waiting for backend... ($($i+1)/$maxWait)"
        } elseif ($i % 10 -eq 0) {
            Write-Log "Still waiting... ($($i+1)/$maxWait)"
        }
    }
    Start-Sleep -Seconds 1
}

if (-not $backendReady) {
    Write-Log "❌ Backend failed to start after ${maxWait}s"
    
    # Show error MessageBox
    Add-Type -AssemblyName System.Windows.Forms
    $errorMsg = "Backend failed to start.`n`nCheck log file:`n$backendLog`n`nThe application will not work correctly."
    [System.Windows.Forms.MessageBox]::Show($errorMsg, "AI Mentor - Backend Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    
    $backendProcess.Kill()
    exit 1
}

# Step 5: Start Frontend
Write-Log ""
Write-Log "Step 5: Starting frontend..."
$frontendPath = Join-Path $scriptDir "app\frontend"

Write-Log "Frontend log: $frontendLog"

# Clear frontend log
"" | Out-File -FilePath $frontendLog

$frontendProcess = Start-HiddenProcess -FilePath "pnpm" -Arguments "run dev" -WorkingDirectory $frontendPath -LogFile $frontendLog
Write-Log "✅ Frontend started (PID: $($frontendProcess.Id))"

Start-Sleep -Seconds 5

# Step 6: Open Browser
Write-Log ""
Write-Log "Step 6: Opening browser..."
Start-Process "http://localhost:3000"
Write-Log "✅ Browser opened"

Write-Log ""
Write-Log "=================================================="
Write-Log "  ✅ AI MENTOR STARTED SUCCESSFULLY"
Write-Log "=================================================="
Write-Log ""
Write-Log "Backend: http://localhost:8000"
Write-Log "Frontend: http://localhost:3000"
Write-Log ""
Write-Log "Services are running in the background."
Write-Log ""
Write-Log "Logs:"
Write-Log "  - Launcher: $launcherLog"
Write-Log "  - Backend: $backendLog"
Write-Log "  - Frontend: $frontendLog"
Write-Log ""