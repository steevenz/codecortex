"""
Suffix index for fast import lookups.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Import_resolvers.Suffix_index
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

from typing import Dict, Set

class SuffixIndex:
    """Index for fast import lookups by file suffix."""

    def __init__(self, files: Set[str]):
        self._suffix_map: Dict[str, Set[str]] = {}
        for f in files:
            for i in range(len(f)):
                suffix = f[i:]
                self._suffix_map.setdefault(suffix, set()).add(f)

    def find(self, suffix: str) -> Set[str]:
        return self._suffix_map.get(suffix, set())
