"""
CodeRepository adapters — VCS and filesystem infrastructure.

:project: CodeCortex
:package: Modules.Coderepository.Adapters
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

from .git.service import Git
from .svn.service import Svn

__all__ = ["Git", "Svn"]
