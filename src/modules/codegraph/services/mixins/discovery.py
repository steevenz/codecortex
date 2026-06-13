"""
Discovery.

:project: CodeCortex
:package: Modules.Codegraph.Services.Mixins.Discovery
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

from __future__ import annotations
import fnmatch
import hashlib
import json
import os
import re
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Set, Any

class FileType(str, Enum):
    CODE = "code"
    DOCUMENT = "document"
    PAPER = "paper"
    IMAGE = "image"
    VIDEO = "video"

# Constants ported from upstream detect.py
CODE_EXTENSIONS = {'.py', '.ts', '.js', '.jsx', '.tsx', '.mjs', '.ejs', '.go', '.rs', '.java', '.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.rb', '.swift', '.kt', '.kts', '.cs', '.scala', '.php', '.lua', '.toc', '.zig', '.ps1', '.ex', '.exs', '.m', '.mm', '.jl', '.vue', '.svelte', '.dart', '.v', '.sv'}
DOC_EXTENSIONS = {'.md', '.mdx', '.txt', '.rst', '.html'}
PAPER_EXTENSIONS = {'.pdf'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
OFFICE_EXTENSIONS = {'.docx', '.xlsx'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v', '.mp3', '.wav', '.m4a', '.ogg'}

CORPUS_WARN_THRESHOLD = 50_000
CORPUS_UPPER_THRESHOLD = 500_000
FILE_COUNT_UPPER = 200

_SENSITIVE_PATTERNS = [
    re.compile(r'(^|[\\/])\.(env|envrc)(\.|$)', re.IGNORECASE),
    re.compile(r'\.(pem|key|p12|pfx|cert|crt|der|p8)$', re.IGNORECASE),
    re.compile(r'(credential|secret|passwd|password|token|private_key)', re.IGNORECASE),
    re.compile(r'(id_rsa|id_dsa|id_ecdsa|id_ed25519)(\.pub)?$'),
    re.compile(r'(\.netrc|\.pgpass|\.htpasswd)$', re.IGNORECASE),
    re.compile(r'(aws_credentials|gcloud_credentials|service.account)', re.IGNORECASE),
]

_PAPER_SIGNALS = [
    re.compile(r'\barxiv\b', re.IGNORECASE),
    re.compile(r'\bdoi\s*:', re.IGNORECASE),
    re.compile(r'\babstract\b', re.IGNORECASE),
    re.compile(r'\bproceedings\b', re.IGNORECASE),
    re.compile(r'\bjournal\b', re.IGNORECASE),
    re.compile(r'\bpreprint\b', re.IGNORECASE),
    re.compile(r'\\cite\{'),
    re.compile(r'\[\d+\]'),
    re.compile(r'\[\n\d+\n\]'),
    re.compile(r'eq\.\s*\d+|equation\s+\d+', re.IGNORECASE),
    re.compile(r'\d{4}\.\d{4,5}'),
    re.compile(r'\bwe propose\b', re.IGNORECASE),
    re.compile(r'\bliterature\b', re.IGNORECASE),
]
_PAPER_SIGNAL_THRESHOLD = 3

_ASSET_DIR_MARKERS = {".imageset", ".xcassets", ".appiconset", ".colorset", ".launchimage"}
_SKIP_DIRS = {
    "venv", ".venv", "env", ".env",
    "node_modules", "__pycache__", ".git",
    "dist", "build", "target", "out",
    "site-packages", "lib64",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".eggs", "*.egg-info",
    "codecortex-out",
}
_SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "poetry.lock", "Gemfile.lock",
    "composer.lock", "go.sum", "go.work.sum",
}

class ArchitecturalDiscoveryMixin:
    """Mixin for file discovery and classification logic."""

    def classify_file(self, path: Path) -> Optional[FileType]:
        if path.name.lower().endswith(".blade.php"):
            return FileType.CODE
        ext = path.suffix.lower()
        if ext in CODE_EXTENSIONS:
            return FileType.CODE
        if ext in PAPER_EXTENSIONS:
            if any(part.endswith(tuple(_ASSET_DIR_MARKERS)) for part in path.parts):
                return None
            return FileType.PAPER
        if ext in IMAGE_EXTENSIONS:
            return FileType.IMAGE
        if ext in DOC_EXTENSIONS:
            if self._looks_like_paper(path):
                return FileType.PAPER
            return FileType.DOCUMENT
        if ext in OFFICE_EXTENSIONS:
            return FileType.DOCUMENT
        if ext in VIDEO_EXTENSIONS:
            return FileType.VIDEO
        return None

    def _is_sensitive(self, path: Path) -> bool:
        name = path.name
        return any(p.search(name) for p in _SENSITIVE_PATTERNS)

    def _looks_like_paper(self, path: Path) -> bool:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:3000]
            hits = sum(1 for pattern in _PAPER_SIGNALS if pattern.search(text))
            return hits >= _PAPER_SIGNAL_THRESHOLD
        except Exception:
            return False

    def _is_noise_dir(self, part: str) -> bool:
        if part in _SKIP_DIRS:
            return True
        if part.endswith("_venv") or part.endswith("_env"):
            return True
        if part.endswith(".egg-info"):
            return True
        return False

    def _load_codecortexignore(self, root: Path) -> List[tuple[Path, str]]:
        patterns: List[tuple[Path, str]] = []
        current = root.resolve()
        while True:
            # Check for both new and legacy ignore files
            for ignore_name in [".codecortexignore", ".graphifyignore"]:
                ignore_file = current / ignore_name
                if ignore_file.exists():
                    for line in ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append((current, line))

            if (current / ".git").exists():
                break
            parent = current.parent
            if parent == current:
                break
            current = parent
        return patterns

    def _is_ignored(self, path: Path, root: Path, patterns: List[tuple[Path, str]]) -> bool:
        if not patterns:
            return False

        def _matches(rel: str, p: str) -> bool:
            parts = rel.split("/")
            if fnmatch.fnmatch(rel, p):
                return True
            if fnmatch.fnmatch(path.name, p):
                return True
            for i, part in enumerate(parts):
                if fnmatch.fnmatch(part, p):
                    return True
                if fnmatch.fnmatch("/".join(parts[:i + 1]), p):
                    return True
            return False

        for anchor, pattern in patterns:
            p = pattern.strip("/")
            if not p:
                continue
            try:
                rel = str(path.relative_to(root)).replace(os.sep, "/")
                if _matches(rel, p):
                    return True
            except ValueError:
                pass
            if anchor != root:
                try:
                    rel_anchor = str(path.relative_to(anchor)).replace(os.sep, "/")
                    if _matches(rel_anchor, p):
                        return True
                except ValueError:
                    pass
        return False

    def discover_files(self, root: Path, follow_symlinks: bool = False) -> Dict[str, Any]:
        """Replacement for upstream detect()."""
        root = root.resolve()
        files: Dict[FileType, List[str]] = {
            FileType.CODE: [],
            FileType.DOCUMENT: [],
            FileType.PAPER: [],
            FileType.IMAGE: [],
            FileType.VIDEO: [],
        }
        total_words = 0
        skipped_sensitive: List[str] = []
        ignore_patterns = self._load_codecortexignore(root)

        # Implementation matches upstream detect() but native
        seen: Set[Path] = set()
        all_files: List[Path] = []

        for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
            dp = Path(dirpath)

            # Prune noise dirs in-place
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".")
                and not self._is_noise_dir(d)
                and not self._is_ignored(dp / d, root, ignore_patterns)
            ]

            for fname in filenames:
                if fname in _SKIP_FILES or fname.startswith("."):
                    continue
                p = dp / fname
                if p not in seen:
                    if not self._is_ignored(p, root, ignore_patterns):
                        if self._is_sensitive(p):
                            skipped_sensitive.append(str(p))
                        else:
                            seen.add(p)
                            all_files.append(p)

        converted_dir = root / "codecortex-out" / "converted"

        for p in all_files:
            ftype = self.classify_file(p)
            if ftype:
                # Office files: skipping complex conversion for now to keep core light,
                # but following the pattern for future integration.
                if ftype == FileType.DOCUMENT and p.suffix.lower() in OFFICE_EXTENSIONS:
                    # Logic for office conversion could go here
                    pass
                files[ftype].append(str(p))

        total_files = sum(len(v) for v in files.values())
        needs_graph = total_words >= CORPUS_WARN_THRESHOLD

        return {
            "files": {k.value: v for k, v in files.items()},
            "total_files": total_files,
            "needs_graph": needs_graph,
            "skipped_sensitive": skipped_sensitive,
        }
