"""
/**
 * @project   CodeCortex
 * @package   CodeRepository/Utils
 * @standard  Aegis-CrossStack-v1.0
 * * Repository utilities — canonical paths, remote URLs, auto-gitignore,
 *   ignore service, max file size config, sibling clone detection.
 *   Ported from GitNexus's git.ts, repo-manager.ts, ignore-service.ts.
 */
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Set, Tuple, Dict, Any

logger = logging.getLogger("CodeCortex.CodeRepository.Utils")

STORAGE_DIR = ".codecortex"

# ═══════════════════════════════════════════════════════════════════
# 1. MAX FILE SIZE CONFIG
# ═══════════════════════════════════════════════════════════════════

DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

def get_max_file_size_bytes() -> int:
    """Get max file size from env var or default."""
    raw = os.getenv("CODECORTEX_MAX_FILE_SIZE_MB", "").strip()
    if raw:
        try:
            return int(raw) * 1024 * 1024
        except ValueError:
            pass
    return DEFAULT_MAX_FILE_SIZE_BYTES


# ═══════════════════════════════════════════════════════════════════
# 2. CANONICAL REPO ROOT (worktree-aware, symlink resolution)
# ═══════════════════════════════════════════════════════════════════

def canonicalize_path(p: str) -> str:
    """Resolve path to canonical form (follows symlinks, normalizes)."""
    resolved = Path(p).resolve()
    try:
        return str(resolved)
    except Exception:
        return str(Path(p).resolve())


def get_current_commit(repo_path: str) -> Optional[str]:
    """Get HEAD commit hash of a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_remote_url(repo_path: str) -> Optional[str]:
    """Get normalized remote origin URL from a git repository."""
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        raw = result.stdout.strip() if result.returncode == 0 else None
        if not raw:
            return None
        return _normalize_remote_url(raw)
    except Exception:
        return None


def _normalize_remote_url(url: str) -> str:
    """Normalize git remote URL for consistent comparison."""
    normalized = url.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    # Lowercase host
    ssh_match = re.match(r"^(git@|[a-zA-Z0-9_-]+@)([^:/]+)([:/].+)$", normalized)
    if ssh_match:
        normalized = f"{ssh_match.group(1)}{ssh_match.group(2).lower()}{ssh_match.group(3)}"
    else:
        url_match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)([^/]+)(/.*)?$", normalized)
        if url_match:
            normalized = f"{url_match.group(1)}{url_match.group(2).lower()}{url_match.group(3) or ''}"
    return normalized


def parse_repo_name_from_url(url: Optional[str]) -> Optional[str]:
    """Extract repository name from a git remote URL."""
    if not url:
        return None
    without_suffix = re.sub(r"\.git/*$", "", url.strip(), flags=re.I).rstrip("/")
    m = re.search(r"[/:]([^/:]+)$", without_suffix)
    return m.group(1) if m else None


def get_inferred_repo_name(repo_path: str) -> Optional[str]:
    """Get repo name from remote URL, or None."""
    url = get_remote_url(repo_path)
    return parse_repo_name_from_url(url)


def get_canonical_repo_root(from_path: str) -> Optional[str]:
    """Get canonical repo root using --git-common-dir (worktree-aware)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=from_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        common_dir = result.stdout.strip()
        if not common_dir:
            return None
        return str(Path(common_dir).parent)
    except Exception:
        return None


def has_git_dir(dir_path: str) -> bool:
    """Check if a directory contains a .git entry."""
    try:
        return (Path(dir_path) / ".git").exists()
    except Exception:
        return False


def is_git_repo(repo_path: str) -> bool:
    """Check if path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_path, capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════
# 3. AUTO-GITIGNORE for .codecortex/
# ═══════════════════════════════════════════════════════════════════

def ensure_codecortex_ignored(repo_path: str) -> None:
    """Add .codecortex/ to .git/info/exclude so it stays ignored."""
    git_dir = Path(repo_path) / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        return
    
    exclude_path = git_dir / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        content = exclude_path.read_text() if exclude_path.exists() else ""
    except Exception:
        content = ""
    
    lines = set(content.splitlines())
    patterns = {f"{STORAGE_DIR}/", f"/{STORAGE_DIR}/"}
    missing = patterns - lines
    
    if not missing:
        return
    
    logger.info(f"Adding {STORAGE_DIR}/ to git info/exclude")
    with open(exclude_path, "a") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        for pat in sorted(missing):
            f.write(f"{pat}\n")


# ═══════════════════════════════════════════════════════════════════
# 4. IGNORE SERVICE (multi-source ignore patterns)
# ═══════════════════════════════════════════════════════════════════

BUILTIN_IGNORE_PATTERNS: Set[str] = {
    ".git/", "__pycache__/", "*.pyc", "*.pyo", "*.db", "*.sqlite",
    ".venv/", "venv/", "node_modules/", "dist/", "build/",
    ".mypy_cache/", ".pytest_cache/", ".ruff_cache/", ".coverage*",
    ".codecortex/", "outputs/", "logs/", "database/", ".env",
    ".DS_Store", "Thumbs.db", "*.swp", "*.swo", "*~",
}


def load_ignore_patterns(repo_path: Path) -> List[str]:
    """Load ignore patterns from multiple sources: built-in, .gitignore, .codecortexignore."""
    patterns: List[str] = list(BUILTIN_IGNORE_PATTERNS)
    
    def _read_ignore_file(path: Path) -> List[str]:
        try:
            with open(path, "r", errors="ignore") as f:
                return [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except Exception:
            return []
    
    gitignore = repo_path / ".gitignore"
    if gitignore.exists():
        patterns.extend(_read_ignore_file(gitignore))
    
    cc_ignore = repo_path / ".codecortexignore"
    if cc_ignore.exists():
        patterns.extend(_read_ignore_file(cc_ignore))
    
    return patterns


def is_ignored(path: str, repo_root: Path, patterns: List[str]) -> bool:
    """Check if a relative path matches any ignore pattern."""
    rel = path.replace("\\", "/")
    for pat in patterns:
        pat = pat.replace("\\", "/")
        if pat.endswith("/"):
            if rel.startswith(pat) or f"/{pat}" in f"/{rel}":
                return True
        else:
            import fnmatch
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(Path(rel).name, pat):
                return True
    return False


# ═══════════════════════════════════════════════════════════════════
# 5. SIBLING CLONE DETECTION
# ═══════════════════════════════════════════════════════════════════

def find_sibling_clones(
    remote_url: str,
    self_path: str,
    registry_entries: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Find other registered entries that share the same remote URL (sibling clones).
    Used to warn when a repo is indexed at one path but queried from another.
    """
    if not remote_url:
        return []
    self_normalized = canonicalize_path(self_path)
    return [
        e for e in registry_entries
        if e.get("remote_url") == remote_url
        and canonicalize_path(e.get("path", "")) != self_normalized
    ]


def check_staleness_against_head(repo_path: str, last_commit: Optional[str]) -> Dict[str, Any]:
    """Check if the index is behind HEAD."""
    if not last_commit:
        return {"is_stale": False, "commits_behind": 0}
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{last_commit}..HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            behind = int(result.stdout.strip() or "0")
            return {
                "is_stale": behind > 0,
                "commits_behind": behind,
                "hint": f"Index is {behind} commit(s) behind HEAD" if behind > 0 else "Up to date"
            }
    except Exception:
        pass
    return {"is_stale": False, "commits_behind": 0}


# ═══════════════════════════════════════════════════════════════════
# 6. REGISTRY METADATA ENHANCEMENT
# ═══════════════════════════════════════════════════════════════════

def build_registry_meta(
    repo_path: str,
    stats: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """Build enhanced registry metadata entry."""
    return {
        "path": canonicalize_path(repo_path),
        "last_commit": get_current_commit(repo_path),
        "remote_url": get_remote_url(repo_path),
        "repo_name": get_inferred_repo_name(repo_path) or Path(repo_path).name,
        "stats": stats or {},
    }
