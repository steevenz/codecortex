"""
Filesystem adapters — disk operations, git/SVN, search, watch, audit.

:project: CodeCortex
:package: Modules.Filesystem.Adapters
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from .reader import DiskReader
from .writer import DiskWriter
from .tree import DiskTree
from .search import DiskSearch
from .deleter import DiskDeleter
from .manager import DiskManager

__all__ = [
    "DiskReader", "DiskWriter", "DiskTree", "DiskSearch",
    "DiskDeleter", "DiskManager",
]
