"""
VCS utilities — git/SVN detection, metadata extraction, URL manipulation.

:project: CodeCortex
:package: Core.Utils.Vcs
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

@lru_cache(maxsize=64)
def detect_vcs_type(repo_path: str | Path) -> str:
    """Detect VCS type at a path: ``'git'``, ``'svn'``, or ``'none'``."""
    p = Path(repo_path)
    if (p / ".git").exists() or (p / ".git").is_file():
        return "git"
    if (p / ".svn").exists():
        return "svn"
    return "none"

def is_git_repo(repo_path: str | Path) -> bool:
    """Check if path is inside a git working tree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(repo_path), capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False

def has_git_dir(dir_path: str | Path) -> bool:
    """Check if a directory contains a .git entry."""
    try:
        return (Path(dir_path) / ".git").exists()
    except Exception:
        return False

def get_canonical_repo_root(from_path: str | Path) -> Optional[str]:
    """Get canonical git repo root (worktree-aware)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=str(from_path), capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        common_dir = result.stdout.strip()
        if not common_dir:
            return None
        return str(Path(common_dir).parent)
    except Exception:
        return None

def get_current_commit(repo_path: str | Path) -> Optional[str]:
    """Get HEAD commit hash of a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path), capture_output=True, text=True, timeout=10,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None

# ── Git Remote URL Utilities ────────────────────────────────────────

def get_remote_url(repo_path: str | Path) -> Optional[str]:
    """Get normalised remote origin URL from a git repository."""
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(repo_path), capture_output=True, text=True, timeout=10,
        )
        raw = result.stdout.strip() if result.returncode == 0 else None
        if not raw:
            return None
        return normalize_remote_url(raw)
    except Exception:
        return None

def normalize_remote_url(url: str) -> str:
    """Normalise a git remote URL for consistent comparison."""
    normalized = url.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    ssh_match = re.match(
        r"^(git@|[a-zA-Z0-9_-]+@)([^:/]+)([:/].+)$", normalized
    )
    if ssh_match:
        normalized = (
            f"{ssh_match.group(1)}{ssh_match.group(2).lower()}{ssh_match.group(3)}"
        )
    else:
        url_match = re.match(
            r"^([a-zA-Z][a-zA-Z0-9+.-]*://)([^/]+)(/.*)?$", normalized
        )
        if url_match:
            normalized = (
                f"{url_match.group(1)}{url_match.group(2).lower()}{url_match.group(3) or ''}"
            )
    return normalized

def parse_repo_name_from_url(url: Optional[str]) -> Optional[str]:
    """Extract repository name from a git remote URL."""
    if not url:
        return None
    without_suffix = re.sub(r"\.git/*$", "", url.strip(), flags=re.I).rstrip("/")
    m = re.search(r"[/:]([^/:]+)$", without_suffix)
    return m.group(1) if m else None

def get_inferred_repo_name(repo_path: str | Path) -> Optional[str]:
    """Get repo name from remote URL, or None."""
    url = get_remote_url(repo_path)
    return parse_repo_name_from_url(url)

# ── VCS Metadata Extraction ─────────────────────────────────────────

def extract_vcs_metadata(repo_path: str | Path, timeout: int = 10) -> Dict[str, Any]:
    """Extract unified VCS metadata from a repository path.

    Returns a dict with keys:
        vcs_type, vcs_url, current_branch, last_commit_hash,
        last_commit_time, current_revision, last_changed_rev.
    Fields that don't apply to the detected VCS are set to None.
    """
    vcs = detect_vcs_type(repo_path)
    if vcs == "git":
        return extract_git_metadata(repo_path, timeout)
    if vcs == "svn":
        return extract_svn_metadata(repo_path, timeout)
    return {
        "vcs_type": "none", "vcs_url": None, "current_branch": None,
        "last_commit_hash": None, "last_commit_time": None,
        "current_revision": None, "last_changed_rev": None,
    }

def extract_git_metadata(repo_path: str | Path, timeout: int = 10) -> Dict[str, Any]:
    """Extract git-specific VCS metadata."""
    rp = str(repo_path)
    result: Dict[str, Any] = {"vcs_type": "git"}

    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=rp, capture_output=True, text=True, timeout=timeout,
        )
        result["current_branch"] = r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        result["current_branch"] = None

    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=rp, capture_output=True, text=True, timeout=timeout,
        )
        result["last_commit_hash"] = r.stdout.strip()[:40] if r.returncode == 0 else None
    except Exception:
        result["last_commit_hash"] = None

    if result.get("last_commit_hash"):
        try:
            r = subprocess.run(
                ["git", "log", "-1", "--format=%cI", "HEAD"],
                cwd=rp, capture_output=True, text=True, timeout=timeout,
            )
            result["last_commit_time"] = r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            result["last_commit_time"] = None

    result["vcs_url"] = get_remote_url(repo_path)
    return result

def extract_svn_metadata(repo_path: str | Path, timeout: int = 10) -> Dict[str, Any]:
    """Extract SVN-specific VCS metadata."""
    rp = str(repo_path)
    result: Dict[str, Any] = {"vcs_type": "svn"}

    for key, item in [
        ("current_revision", "revision"),
        ("last_changed_rev", "last-changed-revision"),
        ("last_commit_time", "last-changed-date"),
        ("vcs_url", "url"),
    ]:
        try:
            r = subprocess.run(
                ["svn", "info", "--show-item", item],
                cwd=rp, capture_output=True, text=True, timeout=timeout,
            )
            val = r.stdout.strip() if r.returncode == 0 else None
            if "revision" in key and val is not None:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            result[key] = val
        except Exception:
            result[key] = None

    return result

def get_changed_files(
    repo_path: str | Path,
    from_ref: str,
    to_ref: str = "HEAD",
    vcs_type: Optional[str] = None,
) -> List[str]:
    """Get list of changed files between two VCS references.

    For Git: ``git diff --name-only <from_ref> <to_ref>``.
    For SVN: ``svn diff --summarize -r <from_ref>:<to_ref>``.
    """
    rp = str(repo_path)
    vcs = vcs_type or detect_vcs_type(rp)
    if vcs == "git":
        try:
            r = subprocess.run(
                ["git", "diff", "--name-only", from_ref, to_ref],
                cwd=rp, capture_output=True, text=True, timeout=30,
            )
            return [ln.strip() for ln in r.stdout.split("\n") if ln.strip()] if r.returncode == 0 else []
        except Exception:
            return []
    if vcs == "svn":
        try:
            r = subprocess.run(
                ["svn", "diff", "--summarize", "-r", f"{from_ref}:{to_ref}"],
                cwd=rp, capture_output=True, text=True, timeout=30,
            )
            return [
                ln.strip().split()[-1]
                for ln in r.stdout.split("\n")
                if ln.strip() and len(ln.strip().split()) >= 2
            ] if r.returncode == 0 else []
        except Exception:
            return []
    return []

def ensure_codecortex_ignored(repo_path: str | Path) -> None:
    """Add .codecortex/ to ``.git/info/exclude`` so it stays ignored."""
    git_dir = Path(repo_path) / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        return

    exclude_path = git_dir / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        content = exclude_path.read_text() if exclude_path.exists() else ""
    except Exception:
        content = ""

    storage_dir = ".codecortex"
    lines = set(content.splitlines())
    patterns = {f"{storage_dir}/", f"/{storage_dir}/"}
    missing = patterns - lines

    if missing:
        with open(exclude_path, "a") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            for pat in sorted(missing):
                f.write(f"{pat}\n")
