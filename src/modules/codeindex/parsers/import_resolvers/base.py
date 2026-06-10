"""
Base import resolver interface.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Import_resolvers.Base
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

from typing import List, Set

class Resolver:
    """Base interface for per-language import resolvers."""

    def resolve(self, import_stmt: str, current_file: str, files: Set[str]) -> List[str]:
        """Resolve an import statement to list of file paths."""
        raise NotImplementedError
