"""
Go import resolver.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Import_resolvers.Go
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

import re
from typing import List, Set

from .base import Resolver

class Go(Resolver):
    """Resolves Go imports: ``import "fmt"`` and ``import "module/path"``."""

    PATTERN = re.compile(r'^\s*import\s+(?:\w+\s+)?["`]([^"`]+)["`]', re.MULTILINE)

    def resolve(self, import_stmt: str, current_file: str, files: Set[str]) -> List[str]:
        resolved = []
        m = self.PATTERN.search(import_stmt)
        if m:
            raw = m.group(1)
            parts = raw.split("/")
            last = f"{parts[-1]}.go" if not parts[-1].endswith(".go") else parts[-1]
            for f in files:
                if f.endswith(last) or raw in f:
                    resolved.append(f)
                    break
        return resolved
