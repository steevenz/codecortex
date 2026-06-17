# CodeCortex Binary Build — PyInstaller single-file executable
# Produces: dist/codecortex.exe (Windows) or dist/codecortex (Unix)

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==> Building CodeCortex CLI binary..."
Write-Host "    Project: $ProjectRoot"

# Check if pyinstaller is available
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: pyinstaller not found. Install with: pip install pyinstaller" -ForegroundColor Red
    exit 1
}

# Clean previous build
if ($Force -and (Test-Path "$ProjectRoot/dist")) {
    Remove-Item -Recurse -Force "$ProjectRoot/dist"
}
if ($Force -and (Test-Path "$ProjectRoot/build")) {
    Remove-Item -Recurse -Force "$ProjectRoot/build"
}

# Build single-file binary
$cliPy = "$ProjectRoot/scripts/cli/codecortex_cli.py"
if (-not (Test-Path $cliPy)) {
    Write-Host "ERROR: codecortex_cli.py not found at $cliPy" -ForegroundColor Red
    exit 1
}

pyinstaller --onefile `
    --name codecortex `
    --clean `
    --add-data "datasets;datasets" `
    --hidden-import src.runtime.bootstrap `
    --hidden-import src.api.orchestration `
    --hidden-import src.modules.codeanalysis.services.audit `
    --hidden-import src.modules.codegraph.services.coddy `
    --hidden-import src.modules.coderepository.services.bootstrap `
    --hidden-import src.modules.filesystem.services.ops `
    --hidden-import src.modules.scaffolder.services.generator `
    --hidden-import src.modules.codetester.api.cli `
    --hidden-import src.modules.knowledgegraph.api.cli `
    --hidden-import src.modules.idegraph.api.cli `
    --hidden-import src.modules.coderefactor.api.cli `
    --distpath "$ProjectRoot/dist" `
    --workpath "$ProjectRoot/build" `
    $cliPy

if ($LASTEXITCODE -eq 0) {
    $Binary = Get-ChildItem "$ProjectRoot/dist/codecortex*"
    Write-Host "==> Build SUCCESS: $($Binary.FullName) ($( [math]::Round($Binary.Length / 1MB, 1) ) MB)" -ForegroundColor Green
} else {
    Write-Host "==> Build FAILED" -ForegroundColor Red
    exit 1
}
