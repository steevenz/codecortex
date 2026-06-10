"""
Import Resolution Pipeline — resolves imports cross-file using per-language resolvers.
Ported from GitNexus's import-processor.ts and import-resolvers/.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Import_resolvers
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

import logging
from typing import Dict, List, Set

from .base import Resolver
from .python import Python
from .typescript import TypeScript
from .go import Go
from .suffix_index import SuffixIndex

logger = logging.getLogger("CodeCortex.CodeIndex.ImportResolution")

RESOLVER_MAP: Dict[str, Resolver] = {
    "python": Python(),
    "typescript": TypeScript(),
    "javascript": TypeScript(),
    "tsx": TypeScript(),
    "go": Go(),
}

def resolve_imports_for_file(
    file_path: str,
    content: str,
    language: str,
    all_files: Set[str],
    suffix_index: SuffixIndex,
) -> List[str]:
    """Resolve all imports in a file to their target file paths."""
    resolver = RESOLVER_MAP.get(language)
    if not resolver:
        return []

    resolved = []
    for line in content.split("\n"):
        try:
            targets = resolver.resolve(line, file_path, all_files)
            resolved.extend(targets)
        except Exception as e:
            logger.debug(f"Import resolution failed for {file_path}: {e}")
    return list(set(resolved))

def build_import_map(
    files: List[Dict[str, str]],
) -> Dict[str, List[str]]:
    """Build a complete import map for a list of files.

    Each file dict should have: path, content, language.
    Returns dict[file_path, List[resolved_target_paths]].
    """
    all_files = {f["path"] for f in files}
    suffix_index = SuffixIndex(all_files)
    import_map: Dict[str, List[str]] = {}

    for f in files:
        resolved = resolve_imports_for_file(
            file_path=f["path"],
            content=f.get("content", ""),
            language=f.get("language", "python"),
            all_files=all_files,
            suffix_index=suffix_index,
        )
        if resolved:
            import_map[f["path"]] = resolved

    return import_map

__all__ = [
    "Resolver",
    "Python",
    "TypeScript",
    "Go",
    "SuffixIndex",
    "RESOLVER_MAP",
    "resolve_imports_for_file",
    "build_import_map",
]
