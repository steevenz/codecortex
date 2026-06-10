#!/bin/bash
# CodeCortex Quick Start Script (Unix)
# ------------------------------------
# One-command setup for end users.
# Run this from the project root directory.

set -e

echo -e "\n\033[0;36m  CodeCortex Quick Start\033[0m\n"

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"
echo -e "\033[0;90m  Project: $PROJECT_ROOT\033[0m"

# 1. Ensure .env exists
if [ ! -f ".env" ]; then
    echo -e "\033[0;33m  Creating .env from template...\033[0m"
    cp .env.example .env
else
    echo -e "\033[0;90m  .env already exists\033[0m"
fi

# 2. Install dependencies
if command -v uv &> /dev/null; then
    echo -e "\033[0;33m  Syncing dependencies with uv...\033[0m"
    uv sync --no-dev
else
    echo -e "\033[0;33m  uv not found. Falling back to pip...\033[0m"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    .venv/bin/python -m pip install -e . --quiet
fi

# 3. Generate API key if missing
if grep -qE "^CODECORTEX_CLIENT_API_KEY=\s*$" .env 2>/dev/null || ! grep -q "CODECORTEX_CLIENT_API_KEY=" .env 2>/dev/null; then
    echo -e "\033[0;33m  Generating API key...\033[0m"
    if command -v uv &> /dev/null; then
        uv run python scripts/server/keygen.py --install --force
    else
        .venv/bin/python scripts/server/keygen.py --install --force
    fi
else
    echo -e "\033[0;90m  API key already configured\033[0m"
fi

# 4. Success message
echo -e "\n\033[0;32m  SETUP COMPLETE\033[0m"
echo -e "\n\033[0;37m  Next steps:\033[0m"
echo -e "\033[0;90m  1. Add this to your MCP client config:\033[0m"
echo -e '\033[0;36m     { "mcpServers": { "codecortex": { "command": "npx", "args": ["-y", "codecortex"] } } }\033[0m'
echo -e "\033[0;90m  2. Restart your IDE/CLI\033[0m"
echo -e "\033[0;90m  3. Test: ask your AI to analyze a codebase\033[0m\n"
