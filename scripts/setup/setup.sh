#!/bin/bash
# CodeCortex Setup Script (Unix)
# -----------------------------------
# Initializes the environment for CodeCortex.
# For a faster one-command experience, use: bash scripts/setup/quickstart.sh

echo -e "\033[0;36mStarting CodeCortex Setup...\033[0m"

CODECORTEX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CODECORTEX_ROOT"

# 1. Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo -e "\033[0;33mCreating .env from .env.example...\033[0m"
    cp .env.example .env
else
    echo -e "\033[0;90m.env already exists, skipping.\033[0m"
fi

# 2. Sync dependencies
if command -v uv &> /dev/null; then
    echo -e "\033[0;33mSyncing dependencies with uv...\033[0m"
    uv sync --no-dev
else
    echo -e "\033[0;33muv not found. Falling back to pip...\033[0m"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    .venv/bin/python -m pip install -e . --quiet
fi

# 3. Generate API key if missing
if grep -qE "^CODECORTEX_CLIENT_API_KEY=\s*$" .env 2>/dev/null || ! grep -q "CODECORTEX_CLIENT_API_KEY=" .env 2>/dev/null; then
    echo -e "\033[0;33mGenerating API key...\033[0m"
    if command -v uv &> /dev/null; then
        uv run python scripts/server/keygen.py --install --force
    else
        .venv/bin/python scripts/server/keygen.py --install --force
    fi
else
    echo -e "\033[0;90mAPI key already configured, skipping.\033[0m"
fi

echo -e "\033[0;32mSetup Complete! CodeCortex is ready.\033[0m"
echo -e "\033[0;90mNext: Add to your MCP client config and restart your IDE.\033[0m"
