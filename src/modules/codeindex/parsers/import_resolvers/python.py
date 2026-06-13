"""
Python import resolver.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Import_resolvers.Python
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

import re
from typing import List, Set

from .base import Resolver

class Python(Resolver):
    """Resolves Python imports: ``from foo.bar import Baz`` and ``import foo``."""

    PATTERN_IMPORT = re.compile(r"^\s*import\s+(.+)$", re.MULTILINE)
    PATTERN_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+(.+)$", re.MULTILINE)

    def resolve(self, import_stmt: str, current_file: str, files: Set[str]) -> List[str]:
        resolved = []
        m = self.PATTERN_FROM.match(import_stmt)
        if m:
            module_path = m.group(1).replace(".", "/")
            candidates = [
                f"{module_path}.py",
                f"{module_path}/__init__.py",
                f"{module_path}/{m.group(2).split(',')[0].strip()}.py",
            ]
            for c in candidates:
                if c in files:
                    resolved.append(c)
        else:
            m = self.PATTERN_IMPORT.match(import_stmt)
            if m:
                for name in m.group(1).split(","):
                    name = name.strip().split(" as ")[0].strip()
                    module_path = name.replace(".", "/")
                    for c in [f"{module_path}.py", f"{module_path}/__init__.py"]:
                        if c in files:
                            resolved.append(c)
        return resolved
