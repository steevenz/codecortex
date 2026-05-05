#!/bin/bash
# CodeCortex Setup Script (Unix)
# -----------------------------------
# This script initializes the development environment for CodeCortex.

echo -e "\033[0;36mStarting CodeCortex Setup...\033[0m"

CODECORTEX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# 0. Vendored upstreams are required for detached mode
VENDORED_CHECKS=(
  "$CODECORTEX_ROOT/vendor/upstreams/codegraph"
  "$CODECORTEX_ROOT/vendor/upstreams/codeindex"
  "$CODECORTEX_ROOT/vendor/upstreams/graphify"
  "$CODECORTEX_ROOT/src/domain/codegraph/upstream/codegraphcontext"
  "$CODECORTEX_ROOT/src/domain/codeindex/upstream/code_index_mcp"
  "$CODECORTEX_ROOT/src/domain/graphify/upstream/graphify"
)
for p in "${VENDORED_CHECKS[@]}"; do
  if [ ! -d "$p" ]; then
    echo -e "\033[0;31mMissing vendored upstream artifact: $p\033[0m"
    echo -e "\033[0;33mRun: python scripts/harvest_upstreams.py --source pythons --mode both --clone-missing\033[0m"
    exit 1
  fi
done

# Optional: fetch external upstream clones (only for refreshing vendor)
if [ "${CODECORTEX_FETCH_UPSTREAMS:-0}" = "1" ]; then
  if ! command -v git &> /dev/null; then
    echo -e "\033[0;31mgit not found. Please install Git to fetch upstream repos.\033[0m"
    exit 1
  fi
  declare -A UPSTREAMS
  UPSTREAMS[codegraph]="https://github.com/steevenz/codegraph.git"
  UPSTREAMS[codeindex]="https://github.com/steevenz/codeindex.git"
  UPSTREAMS[graphify]="https://github.com/steevenz/graphify.git"
  for name in "${!UPSTREAMS[@]}"; do
    target="$PYTHONS_DIR/$name"
    if [ ! -d "$target" ]; then
      echo -e "\033[0;33mCloning upstream repo '$name' into: $target\033[0m"
      git clone "${UPSTREAMS[$name]}" "$target"
      if [ $? -ne 0 ]; then
        echo -e "\033[0;31mFailed to clone '$name'. Please check git auth/network.\033[0m"
        exit 1
      fi
    fi
  done
fi

# 1. Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo -e "\033[0;33mCreating .env from .env.example...\033[0m"
    cp .env.example .env
else
    echo -e "\033[0;90m.env already exists, skipping.\033[0m"
fi

# 2. Sync dependencies using uv
if command -v uv &> /dev/null; then
    echo -e "\033[0;33mSyncing dependencies with uv...\033[0m"
    uv sync
else
    echo -e "\033[0;31muv not found. Please install uv first (https://github.com/astral-sh/uv).\033[0m"
    exit 1
fi

echo -e "\033[0;32mSetup Complete! CodeCortex is ready.\033[0m"
