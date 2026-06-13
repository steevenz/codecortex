"""
Path utilities — normalisation, relative resolution, glob expansion.

:project: CodeCortex
:package: Core.Utils.Path
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import os
import glob as glob_mod
from functools import lru_cache
from pathlib import Path
from typing import Optional

@lru_cache(maxsize=4096)
def norm_path(p: str) -> str:
    """Normalise Windows backslashes to forward slashes."""
    return p.replace("\\", "/")

def normalize_relpath(root: Path, p: str) -> Optional[str]:
    """Resolve a path string to a relative path under root, with traversal guard.

    Args:
        root: The base directory.
        p: The path to resolve (absolute or relative, string).

    Returns:
        Normalised relative path string (forward slashes), or None if invalid.
    """
    if not isinstance(p, str) or not p.strip():
        return None
    raw = p.strip().replace("\\", "/")
    if raw.startswith("./"):
        raw = raw[2:]
    if ".." in raw:
        return None
    try:
        pp = Path(p)
        if pp.is_absolute():
            rel = pp.resolve().relative_to(root.resolve())
            return str(rel).replace("\\", "/")
        return str(Path(raw)).replace("\\", "/").strip("/")
    except (ValueError, OSError):
        return None

def resolve_glob(pattern: str, cwd: Optional[Path] = None) -> Optional[str]:
    """Resolve a glob pattern to the first matching filesystem path.

    Args:
        pattern: A glob pattern (e.g. ``**/pytest``).
        cwd: Working directory for glob expansion. Uses CWD if None.

    Returns:
        First matching path as string, or None if no match.
    """
    try:
        results = glob_mod.glob(pattern, root_dir=cwd, recursive=True)
        for p in results:
            resolved = (cwd / p).resolve() if cwd else Path(p).resolve()
            if resolved.exists():
                return str(resolved)
        return None
    except (ValueError, OSError):
        return None

def canonicalize(path: str) -> str:
    """Resolve a path string to its canonical form (follows symlinks)."""
    try:
        return str(Path(path).resolve())
    except Exception:
        return str(Path(path).resolve())
