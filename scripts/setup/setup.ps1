# CodeCortex Setup Script (Windows)
# -----------------------------------
# Initializes the environment for CodeCortex.
# For a faster one-command experience, use: .\scripts\setup\quickstart.ps1

Write-Host "Starting CodeCortex Setup..." -ForegroundColor Cyan

$codecortexRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $codecortexRoot

# 1. Copy .env.example if .env doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
} else {
    Write-Host ".env already exists, skipping." -ForegroundColor Gray
}

# 2. Sync dependencies
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "Syncing dependencies with uv..." -ForegroundColor Yellow
    uv sync --no-dev
} else {
    Write-Host "uv not found. Falling back to pip..." -ForegroundColor Yellow
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }
    & ".venv\Scripts\python.exe" -m pip install -e . --quiet
}

# 3. Generate API key if missing
$envContent = Get-Content ".env" -Raw
if ($envContent -match "CODECORTEX_CLIENT_API_KEY=\s*$" -or $envContent -notmatch "CODECORTEX_CLIENT_API_KEY=") {
    Write-Host "Generating API key..." -ForegroundColor Yellow
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        uv run python scripts/server/keygen.py --install --force
    } else {
        & ".venv\Scripts\python.exe" scripts/server/keygen.py --install --force
    }
} else {
    Write-Host "API key already configured, skipping." -ForegroundColor Gray
}

Write-Host "`nSetup Complete! CodeCortex is ready." -ForegroundColor Green
Write-Host "Next: Add to your MCP client config and restart your IDE." -ForegroundColor Gray
