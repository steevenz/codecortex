"""
/**
 * @project   CodeCortex
 * @package   CodeIndex/ImportResolvers
 * @standard  Aegis-CrossStack-v1.0
 * * Import Resolution Pipeline — resolves imports cross-file using per-language resolvers.
 *   Ported from GitNexus's import-processor.ts and import-resolvers/.
 */
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.CodeIndex.ImportResolution")


class ImportResolver:
    """Base interface for per-language import resolvers."""

    def resolve(self, import_stmt: str, current_file: str, files: Set[str]) -> List[str]:
        """Resolve an import statement to list of file paths."""
        raise NotImplementedError


class PythonImportResolver(ImportResolver):
    """Resolves Python imports: `from foo.bar import Baz` and `import foo`."""

    PATTERN_IMPORT = re.compile(r"^\s*import\s+(.+)$", re.MULTILINE)
    PATTERN_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+(.+)$", re.MULTILINE)

    def resolve(self, import_stmt: str, current_file: str, files: Set[str]) -> List[str]:
        resolved = []
        m = self.PATTERN_FROM.match(import_stmt)
        if m:
            module_path = m.group(1).replace(".", "/")
            candidates = [f"{module_path}.py", f"{module_path}/__init__.py",
                          f"{module_path}/{m.group(2).split(',')[0].strip()}.py"]
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


class TypeScriptImportResolver(ImportResolver):
    """Resolves TypeScript/JS imports: `import { X } from './foo'`."""

    PATTERN = re.compile(
        r"import\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+['\"]([^'\"]+)['\"]"
    )
    PATTERN_REQUIRE = re.compile(r"(?:const|let|var)\s+\w+\s*=\s*require\(['\"]([^'\"]+)['\"]\)")

    def resolve(self, import_stmt: str, current_file: str, files: Set[str]) -> List[str]:
        resolved = []
        for pattern in (self.PATTERN, self.PATTERN_REQUIRE):
            m = pattern.search(import_stmt)
            if m:
                raw_path = m.group(1)
                current_dir = str(Path(current_file).parent).replace("\\", "/")
                # Handle relative paths
                if raw_path.startswith("./") or raw_path.startswith("../"):
                    full = str(Path(current_dir) / raw_path)
                    full = full.replace("\\", "/")
                    # Normalize: remove leading ./ and keep relative if possible
                    for known_file in files:
                        if known_file.endswith(full) or full.endswith(known_file) or known_file in full or full in known_file:
                            resolved.append(known_file)
                else:
                    # Module name — try matching in files
                    for f in files:
                        if raw_path in f or f.endswith(f"/{raw_path}"):
                            resolved.append(f)
        return list(set(resolved))


class GoImportResolver(ImportResolver):
    """Resolves Go imports: `import "fmt"` and `import "module/path"`."""

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


RESOLVER_MAP: Dict[str, ImportResolver] = {
    "python": PythonImportResolver(),
    "typescript": TypeScriptImportResolver(),
    "javascript": TypeScriptImportResolver(),
    "tsx": TypeScriptImportResolver(),
    "go": GoImportResolver(),
}


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
    files: List[Dict[str, str]]
) -> Dict[str, List[str]]:
    """
    Build a complete import map for a list of files.

    Each file dict should have: path, content, language.
    Returns dict[file_path, List[resolved_target_paths]]
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
