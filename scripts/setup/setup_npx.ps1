# CodeCortex MCP Setup Script for NPX (Windows PowerShell)
# ---------------------------------------------------------
# This script sets up CodeCortex MCP server to be used with npx

Write-Host "Setting up CodeCortex MCP for NPX..." -ForegroundColor Cyan

$CODECORTEX_ROOT = Split-Path -Parent $PSScriptRoot | Split-Path -Parent
$PYTHONS_DIR = Split-Path -Parent $PSScriptRoot

# Check if uv is available
$uvAvailable = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)

if ($uvAvailable) {
    Write-Host "Using uv for dependency management..." -ForegroundColor Yellow
    Set-Location $CODECORTEX_ROOT
    uv sync
} else {
    Write-Host "uv not found, using direct Python..." -ForegroundColor Yellow
}

# Create .env if not exists
$envPath = Join-Path $CODECORTEX_ROOT ".env"
$envExamplePath = Join-Path $CODECORTEX_ROOT ".env.example"

if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
        Write-Host "Created .env from .env.example" -ForegroundColor Green
    } else {
        Write-Host "No .env.example found, creating default .env..." -ForegroundColor Yellow
        @"
CODECORTEX_DB_PATH=./database/codecortex.db
CODECORTEX_GRAPH_BACKEND=kuzu
CODECORTEX_MAX_REPOS=50
CODECORTEX_TRANSPORT=stdio
"@ | Out-File -FilePath $envPath -Encoding utf8
    }
}

# Create database directory
$dbDir = Join-Path $CODECORTEX_ROOT "database"
if (-not (Test-Path $dbDir)) {
    New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
}

# Generate key for webhook (optional)
$keyPath = Join-Path $CODECORTEX_ROOT ".webhook_key"
if (-not (Test-Path $keyPath)) {
    $key = [System.Guid]::NewGuid().ToString()
    $key | Out-File -FilePath $keyPath -Encoding utf8
    Write-Host "Generated webhook secret key" -ForegroundColor Green
}

Write-Host "" -ForegroundColor Cyan
Write-Host "CodeCortex MCP Setup Complete!" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "Usage in Claude Desktop / Trae IDE:" -ForegroundColor Yellow
Write-Host '  "mcpServers": {' -ForegroundColor Gray
Write-Host '    "codecortex": {' -ForegroundColor Gray
Write-Host '      "command": "npx",' -ForegroundColor Gray
Write-Host '      "args": ["codecortex-mcp"],' -ForegroundColor Gray
Write-Host '      "env": {' -ForegroundColor Gray
Write-Host '        "CODECORTEX_DB_PATH": "${HOME}/.coddy/codecortex/db.sqlite",' -ForegroundColor Gray
Write-Host '        "CODECORTEX_GRAPH_BACKEND": "kuzu",' -ForegroundColor Gray
Write-Host '        "CODECORTEX_MAX_REPOS": "50"' -ForegroundColor Gray
Write-Host '      }' -ForegroundColor Gray
Write-Host '    }' -ForegroundColor Gray
Write-Host '  }' -ForegroundColor Gray
