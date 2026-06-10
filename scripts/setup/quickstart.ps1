# CodeCortex Quick Start Script (Windows)
# ---------------------------------------
# One-command setup for end users.
# Run this from the project root directory.

$ErrorActionPreference = "Stop"
Write-Host "`n  CodeCortex Quick Start`n" -ForegroundColor Cyan

$ProjectRoot = $PSScriptRoot | Split-Path | Split-Path
Set-Location $ProjectRoot
Write-Host "  Project: $ProjectRoot" -ForegroundColor Gray

# 1. Ensure .env exists
if (-not (Test-Path ".env")) {
    Write-Host "  Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
} else {
    Write-Host "  .env already exists" -ForegroundColor Gray
}

# 2. Install dependencies
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "  Syncing dependencies with uv..." -ForegroundColor Yellow
    uv sync --no-dev
} else {
    Write-Host "  uv not found. Falling back to pip..." -ForegroundColor Yellow
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }
    & ".venv\Scripts\python.exe" -m pip install -e . --quiet
}

# 3. Generate API key if missing
$envContent = Get-Content ".env" -Raw
if ($envContent -match "CODECORTEX_CLIENT_API_KEY=\s*$" -or $envContent -notmatch "CODECORTEX_CLIENT_API_KEY=") {
    Write-Host "  Generating API key..." -ForegroundColor Yellow
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        uv run python scripts/server/keygen.py --install --force
    } else {
        & ".venv\Scripts\python.exe" scripts/server/keygen.py --install --force
    }
} else {
    Write-Host "  API key already configured" -ForegroundColor Gray
}

# 4. Success message
Write-Host "`n  SETUP COMPLETE" -ForegroundColor Green
Write-Host "`n  Next steps:" -ForegroundColor White
Write-Host "  1. Add this to your MCP client config:" -ForegroundColor Gray
Write-Host '     { "mcpServers": { "codecortex": { "command": "npx", "args": ["-y", "codecortex"] } } }' -ForegroundColor Cyan
Write-Host "  2. Restart your IDE/CLI" -ForegroundColor Gray
Write-Host "  3. Test: ask your AI to analyze a codebase`n" -ForegroundColor Gray
