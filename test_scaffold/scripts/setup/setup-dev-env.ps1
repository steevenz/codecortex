# @project   Myawesomeproject
# @category  Scripts/Setup
# @author    Steeven Andrian
# @copyright (c) Steeven Andrian
# @fileoverview Development environment setup script (PowerShell).
#
# Usage:
#   .\scripts\setup\setup-dev-env.ps1
#   .\scripts\setup\setup-dev-env.ps1 -Clean

param(
    [switch]$Clean
)

$ProjectName = "Myawesomeproject"
$VenvDir = "venv"

Write-Host "============================================"
Write-Host "  $ProjectName - Development Setup"
Write-Host "============================================"
Write-Host ""

if ($Clean) {
    Write-Host "Cleaning existing venv..."
    if (Test-Path $VenvDir) {
        Remove-Item -Recurse -Force $VenvDir
    }
    Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "   Done."
    Write-Host ""
}

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..."
    python -m venv $VenvDir
    Write-Host "   Done."
} else {
    Write-Host "Virtual environment already exists."
}

Write-Host "Activating virtual environment..."
& "$VenvDir\Scripts\Activate.ps1"

Write-Host "Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"
Write-Host "   Done."

Write-Host ""
Write-Host "============================================"
Write-Host "  Setup complete!"
Write-Host ""
Write-Host "  Activate: .\$VenvDir\Scripts\Activate.ps1"
Write-Host "  Run:      python -m src.main"
Write-Host "  Test:     python -m pytest"
Write-Host "============================================"
