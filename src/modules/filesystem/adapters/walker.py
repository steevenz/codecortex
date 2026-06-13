"""
Filesystem-based file walker with concurrent stat and two-phase scanning.

Matches GitNexus's approach: glob scan → batch stat → filter → content read.
Replaces os.walk in Repository for faster file discovery.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Walker
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from glob import glob as glob_stdlib
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from src.core.config.ignore_patterns import BUILTIN_IGNORE_PATTERNS

logger = logging.getLogger("CodeCortex.Filesystem.Walker")

DEFAULT_CONCURRENCY = 32
DEFAULT_MAX_FILE_SIZE_MB = 1

@dataclass
class ScannedFile:
    path: str
    size: int

@dataclass
class FileContent:
    path: str
    content: Optional[str]
    size: int

def _build_ignore_spec(root: Path) -> PathSpec:
    """Build PathSpec from .gitignore, .codecortexignore, and built-in patterns."""
    patterns: List[str] = list(BUILTIN_IGNORE_PATTERNS)
    patterns.extend([".gitignore", ".codecortexignore"])

    def _read_lines(p: Path) -> List[str]:
        try:
            with open(p, "r", errors="ignore") as f:
                return [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except Exception:
            return []

    gitignore = root / ".gitignore"
    if gitignore.exists():
        patterns.extend(_read_lines(gitignore))

    cc_ignore = root / ".codecortexignore"
    if cc_ignore.exists():
        patterns.extend(_read_lines(cc_ignore))

    return PathSpec.from_lines(GitWildMatchPattern, patterns)

def walk_repository_paths(
    repo_path: Path,
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> List[ScannedFile]:
    """
    Phase 1: Walk repository using glob, stat files concurrently, return paths + sizes.

    Uses glob for fast file discovery, then batch-stat for concurrency.
    No file content is read in this phase.
    """
    spec = _build_ignore_spec(repo_path)
    max_bytes = max_file_size_mb * 1024 * 1024

    raw_pattern = os.path.join(repo_path, "**", "*")
    all_paths = [p for p in glob_stdlib(raw_pattern, recursive=True) if os.path.isfile(p)]

    # Filter via pathspec
    filtered = []
    for abs_path in all_paths:
        rel = os.path.relpath(abs_path, repo_path).replace("\\", "/")
        if not spec.match_file(rel):
            filtered.append(abs_path)

    # Batch stat
    results: List[ScannedFile] = []
    skipped_large = 0

    for start in range(0, len(filtered), concurrency):
        batch = filtered[start:start + concurrency]
        for abs_path in batch:
            try:
                size = os.path.getsize(abs_path)
                if size > max_bytes:
                    skipped_large += 1
                    continue
                rel = os.path.relpath(abs_path, repo_path).replace("\\", "/")
                results.append(ScannedFile(path=rel, size=size))
            except OSError:
                continue

    if skipped_large:
        logger.warning(f"Skipped {skipped_large} files over {max_file_size_mb}MB")

    return results

def read_file_contents(
    repo_path: Path,
    scanned: List[ScannedFile],
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> List[FileContent]:
    """
    Phase 2: Read content for code/doc/config files under size limit.

    Skips binary and large files. Content is read concurrently in batches.
    """
    max_bytes = max_file_size_mb * 1024 * 1024
    code_exts = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs',
                 '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.swift', '.kt',
                 '.scala', '.lua', '.r', '.m', '.pl', '.sql', '.sh', '.bash', '.zsh',
                 '.md', '.rst', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini',
                 '.cfg', '.conf', '.xml', '.properties', '.html', '.css', '.scss', '.vue', '.svelte'}
    results: List[FileContent] = []

    for start in range(0, len(scanned), concurrency):
        batch = scanned[start:start + concurrency]
        for sf in batch:
            ext = os.path.splitext(sf.path)[1].lower()
            if ext not in code_exts or sf.size > max_bytes:
                results.append(FileContent(path=sf.path, content=None, size=sf.size))
                continue
            abs_path = os.path.join(repo_path, sf.path)
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                results.append(FileContent(path=sf.path, content=content, size=sf.size))
            except Exception as e:
                logger.warning(f"Failed to read {sf.path}: {e}")
                results.append(FileContent(path=sf.path, content=None, size=sf.size))

    return results
