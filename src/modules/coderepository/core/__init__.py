"""
CodeRepository core domain — repository models, stores, and utilities.

:project: CodeCortex
:package: Modules.Coderepository.Core
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from .store import ICodeRepositoryStore
from .repository_store import RepositoryStore
from .repository import Repository
from .dto import FileStructure, Summary
from .utils import detect_vcs_type, extract_vcs_metadata

__all__ = [
    "ICodeRepositoryStore",
    "RepositoryStore",
    "Repository",
    "FileStructure",
    "Summary",
    "detect_vcs_type",
    "extract_vcs_metadata",
]
