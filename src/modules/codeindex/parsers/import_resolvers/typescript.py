"""
TypeScript/JavaScript import resolver.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Import_resolvers.Typescript
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

import re
from pathlib import Path
from typing import List, Set

from .base import Resolver

class TypeScript(Resolver):
    """Resolves TypeScript/JS imports: ``import { X } from './foo'``."""

    PATTERN = re.compile(
        r"import\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+['\"]([^'\"]+)['\"]"
    )
    PATTERN_REQUIRE = re.compile(
        r"(?:const|let|var)\s+\w+\s*=\s*require\(['\"]([^'\"]+)['\"]\)"
    )

    def resolve(self, import_stmt: str, current_file: str, files: Set[str]) -> List[str]:
        resolved = []
        for pattern in (self.PATTERN, self.PATTERN_REQUIRE):
            m = pattern.search(import_stmt)
            if m:
                raw_path = m.group(1)
                current_dir = str(Path(current_file).parent).replace("\\", "/")
                if raw_path.startswith("./") or raw_path.startswith("../"):
                    full = str(Path(current_dir) / raw_path)
                    full = full.replace("\\", "/")
                    for known_file in files:
                        if known_file.endswith(full) or full.endswith(known_file) or known_file in full or full in known_file:
                            resolved.append(known_file)
                else:
                    for f in files:
                        if raw_path in f or f.endswith(f"/{raw_path}"):
                            resolved.append(f)
        return list(set(resolved))
