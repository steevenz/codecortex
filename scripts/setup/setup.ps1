# CodeCortex Setup Script (Windows)
# -----------------------------------
# This script initializes the development environment for CodeCortex.

Write-Host "Starting CodeCortex Setup..." -ForegroundColor Cyan

$codecortexRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pythonsDir = Resolve-Path (Join-Path $PSScriptRoot "..\\..")

# 0. Vendored upstreams are required for detached mode
$vendoredChecks = @(
    (Join-Path $codecortexRoot "vendor\\upstreams\\codegraph"),
    (Join-Path $codecortexRoot "vendor\\upstreams\\codeindex"),
    (Join-Path $codecortexRoot "vendor\\upstreams\\graphify"),
    (Join-Path $codecortexRoot "src\\domain\\codegraph\\upstream\\codegraphcontext"),
    (Join-Path $codecortexRoot "src\\domain\\codeindex\\upstream\\code_index_mcp"),
    (Join-Path $codecortexRoot "src\\domain\\graphify\\upstream\\graphify")
)
foreach ($p in $vendoredChecks) {
    if (-not (Test-Path $p)) {
        Write-Host "Missing vendored upstream artifact: $p" -ForegroundColor Red
        Write-Host "Run: python scripts\\harvest_upstreams.py --source pythons --mode both --clone-missing" -ForegroundColor Yellow
        exit 1
    }
}

# Optional: fetch external upstream clones (only for refreshing vendor)
if ($env:CODECORTEX_FETCH_UPSTREAMS -eq "1") {
    if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
        Write-Host "git not found. Please install Git to fetch upstream repos." -ForegroundColor Red
        exit 1
    }
    $upstreams = @(
        @{ Name = "codegraph"; Url = "https://github.com/steevenz/codegraph.git" },
        @{ Name = "codeindex"; Url = "https://github.com/steevenz/codeindex.git" },
        @{ Name = "graphify"; Url = "https://github.com/steevenz/graphify.git" }
    )
    foreach ($u in $upstreams) {
        $target = Join-Path $pythonsDir $u.Name
        if (-not (Test-Path $target)) {
            Write-Host "Cloning upstream repo '$($u.Name)' into: $target" -ForegroundColor Yellow
            git clone $u.Url $target
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Failed to clone '$($u.Name)'. Please check git auth/network." -ForegroundColor Red
                exit 1
            }
        }
    }
}

# 1. Copy .env.example if .env doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
} else {
    Write-Host ".env already exists, skipping." -ForegroundColor Gray
}

# 2. Sync dependencies using uv
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "Syncing dependencies with uv..." -ForegroundColor Yellow
    uv sync
} else {
    Write-Host "uv not found. Please install uv first (https://github.com/astral-sh/uv)." -ForegroundColor Red
    exit 1
}

Write-Host "Setup Complete! CodeCortex is ready." -ForegroundColor Green
