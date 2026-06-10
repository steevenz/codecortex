"""
Database configuration utilities.
Handles database path resolution and project root detection.

:project: CodeCortex
:package: Core.Config.Database
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parents[3]

def get_db_path() -> str:
    """
    Get the database path for CodeCortex.

    Priority:
      1. CODECORTEX_DB_PATH env var
      2. Default: <project_root>/database/codecortex.db
    """
    env_path = os.getenv("CODECORTEX_DB_PATH")
    if env_path:
        return env_path

    project_root = get_project_root()
    return str(project_root / "database" / "codecortex.db")
