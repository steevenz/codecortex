#!/bin/bash
# @project   Myawesomeproject
# @category  Scripts/Setup
# @author    Steeven Andrian
# @copyright (c) Steeven Andrian
# @fileoverview Development environment setup script.
#
# Usage:
#   ./scripts/setup/setup-dev-env.sh
#   ./scripts/setup/setup-dev-env.sh --clean
#
set -euo pipefail

PROJECT_NAME="Myawesomeproject"
VENV_DIR="venv"
CLEAN=false

for arg in "$@"; do
    case $arg in
        --clean) CLEAN=true ;;
    esac
done

echo "============================================"
echo "  $PROJECT_NAME — Development Setup"
echo "============================================"
echo ""

# Clean mode
if [ "$CLEAN" = true ]; then
    echo "🧹 Clean mode: removing existing venv..."
    rm -rf "$VENV_DIR"
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "   Done."
    echo ""
fi

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "   Done."
else
    echo "✅ Virtual environment already exists."
fi

# Activate
echo "⚡ Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"
echo "   Done."

echo ""
echo "============================================"
echo "  ✅ Setup complete!"
echo ""
echo "  Activate: source $VENV_DIR/bin/activate"
echo "  Run:      python -m src.main"
echo "  Test:     python -m pytest"
echo "============================================"
