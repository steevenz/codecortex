"""
Built-in ignore patterns for file scanning and traversal.

:project: CodeCortex
:package: Core.Config.Ignore_patterns
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Set

BUILTIN_IGNORE_PATTERNS: Set[str] = {
    ".git/", "__pycache__/", "*.pyc", "*.pyo", "*.db", "*.db-*",
    "*.sqlite", "*.sqlite-*", ".venv/", "venv/", "vendor/",
    "node_modules/", "dist/", "build/",
    ".mypy_cache/", ".pytest_cache/", ".ruff_cache/", ".coverage*",
    ".codecortex/", "outputs/", "logs/", "database/", ".env",
    ".DS_Store", "Thumbs.db", "*.swp", "*.swo", "*~",
}

def load_ignore_patterns(repo_path: Path) -> List[str]:
    """Load ignore patterns from built-in defaults, .gitignore, and .codecortexignore.

    Args:
        repo_path: Root directory of the repository.

    Returns:
        Combined list of ignore pattern strings.
    """
    patterns: List[str] = list(BUILTIN_IGNORE_PATTERNS)

    def _read(file: Path) -> List[str]:
        try:
            with open(file, "r", errors="ignore") as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except (OSError, PermissionError):
            return []

    gitignore = repo_path / ".gitignore"
    if gitignore.exists():
        patterns.extend(_read(gitignore))

    cc_ignore = repo_path / ".codecortexignore"
    if cc_ignore.exists():
        patterns.extend(_read(cc_ignore))

    return patterns

def is_ignored(path: str, repo_root: Path, patterns: List[str]) -> bool:
    """Check if a relative path matches any ignore pattern.

    Args:
        path: Relative file path to check.
        repo_root: Repository root (used for name matching).
        patterns: List of glob-style ignore patterns.

    Returns:
        True if the path should be ignored.
    """
    import fnmatch

    rel = path.replace("\\", "/")
    for pat in patterns:
        pat = pat.replace("\\", "/")
        if pat.endswith("/"):
            if rel.startswith(pat) or f"/{pat}" in f"/{rel}":
                return True
        else:
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(Path(rel).name, pat):
                return True
    return False
