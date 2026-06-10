"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.services
:standard: Aegis-IdeGraph-v1.0

Storage — SQLite persistence for cross-IDE memories (re-export from sqlite_storage).
"""

from src.modules.idegraph.services.sqlite_storage import Storage

__all__ = ["Storage"]
