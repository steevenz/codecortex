"""
CodeRepository filesystem adapters — file reading and SQLite persistence.

:project: CodeCortex
:package: Modules.Coderepository.Adapters.Filesystem
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from .file_reader import FileReader
from .sqlite_store import SQLiteCodeRepositoryStore

__all__ = ["FileReader", "SQLiteCodeRepositoryStore"]
