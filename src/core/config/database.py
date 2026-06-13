"""
Database configuration utilities.
Handles database path resolution and project root detection.

:project: CodeCortex
:package: Core.Config.Database
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger("CodeCortex.Core.Config.Database")

_CODECORTEX_DIR = Path.home() / ".coddy" / "codecortex"

def get_data_dir() -> Path:
    """
    Get the CodeCortex data directory (~/.coddy/codecortex).

    This is the single source of truth for all persisted state:
      - codecortex.pid         — PID lockfile (Node ↔ Python handshake)
      - codecortex.killed      — Killed-PID cache (cascade prevention)
      - data/codecortex.db     — SQLite database
      - data/                  — Data files
      - global/kuzudb          — KuzuDB graph backend
      - logs/codecortex.log    — Rotating JSON logs
      - neocortex.json         — Neocortex cognitive bridge config
      - update_signal.json     — AI update signal
      - update.json            — Update metadata

    Override with CODECORTEX_DATA_DIR env var.
    """
    env_dir = os.getenv("CODECORTEX_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
    else:
        data_dir = _CODECORTEX_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parents[3]

def _get_old_db_path() -> Path:
    """
    Get the legacy database path (<project_root>/database/codecortex.db).

    Used only for auto-migration. Will be removed in a future version.
    """
    return get_project_root() / "database" / "codecortex.db"

def get_db_path() -> str:
    """
    Get the database path for CodeCortex.

    Priority:
      1. CODECORTEX_DB_PATH env var
      2. Default: ~/.coddy/codecortex/data/codecortex.db

    Auto-migration: if old path (<project_root>/database/codecortex.db) exists
    and new path does not, the database is automatically copied (not moved)
    to the new location during the first call.
    """
    env_path = os.getenv("CODECORTEX_DB_PATH")
    if env_path:
        return env_path

    data_dir = get_data_dir()
    db_path = data_dir / "data" / "codecortex.db"

    # Auto-migrate from legacy location if new path doesn't exist yet
    if not db_path.exists():
        old_path = _get_old_db_path()
        if old_path.exists():
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(old_path), str(db_path))
                logger.info(
                    "Auto-migrated database: %s → %s",
                    old_path, db_path,
                )
            except Exception as e:
                logger.warning(
                    "Failed to migrate database from %s: %s. "
                    "Falling back to old location.",
                    old_path, e,
                )
                return str(old_path)

    return str(db_path)
