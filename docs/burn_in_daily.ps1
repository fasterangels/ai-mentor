# burn_in_daily runner: set preset env, run ops burn-in-run once, exit non-zero if critical alerts.
# Usage: from repo root, .\docs\burn_in_daily.ps1   or   pwsh -File docs/burn_in_daily.ps1
$ErrorActionPreference = "Stop"
$env:ACTIVATION_ENABLED = "true"
$env:ACTIVATION_MODE = "burn_in"
$env:ACTIVATION_MAX_MATCHES = "1"
$env:LIVE_IO_ALLOWED = "true"
$env:LIVE_WRITES_ALLOWED = "true"
$env:ACTIVATION_KILL_SWITCH = "false"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repoRoot "tools\ops.py"))) {
    $repoRoot = (Get-Location).Path
}
$opsPy = Join-Path $repoRoot "tools\ops.py"
if (-not (Test-Path $opsPy)) {
    Write-Error "tools/ops.py not found. Run from repo root or ensure docs/burn_in_daily.ps1 is under repo."
    exit 2
}

$out = & python $opsPy burn-in-run --activation 2>&1
$lastLine = ($out | Select-Object -Last 1) -replace "^\s+|\s+$", ""
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# Format: run_id,status,alerts_count,activated,bundle_dir
$parts = $lastLine -split ",", 5
if ($parts.Count -lt 4) { exit 1 }
$status = $parts[1]
$alertsCount = 0
if ($parts[2] -match "^\d+$") { [int]::TryParse($parts[2], [ref]$alertsCount) | Out-Null }
if ($status -ne "ok" -or $alertsCount -gt 0) { exit 1 }
exit 0
