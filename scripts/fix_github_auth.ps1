# Fix GitHub auth: verify after you have run "gh auth login" once.
# Run from repo root: .\scripts\fix_github_auth.ps1
# Step 1 (interactive) you must run yourself: gh auth login

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== Step 2: gh auth status ===" -ForegroundColor Cyan
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run first: gh auth login (choose GitHub.com, HTTPS, then browser or token)" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== Step 3: gh auth setup-git ===" -ForegroundColor Cyan
gh auth setup-git

Write-Host "`n=== Step 4: git ls-remote origin ===" -ForegroundColor Cyan
git remote get-url origin
$heads = git ls-remote --heads origin 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "git ls-remote failed: $heads" -ForegroundColor Red
    exit 1
}
$heads | Select-Object -First 5

Write-Host "`n=== Step 5: gh repo view + pr list ===" -ForegroundColor Cyan
gh repo view --json nameWithOwner,defaultBranchRef
gh pr list --state open --limit 5

Write-Host "`n=== All checks passed ===" -ForegroundColor Green
