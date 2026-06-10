"""
Repository utilities — canonical paths, remote URLs, auto-gitignore,
ignore service, max file size config, sibling clone detection.
Delegates shared implementations to ``src.core.utils.vcs`` and
``src.core.config.ignore_patterns``.

:project: CodeCortex
:package: Modules.Coderepository.Core.Utils
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRepository-v1.0
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

# ── Re-exports from core ─────────────────────────────────────────────

from src.core.utils.path import canonicalize as canonicalize_path
from src.core.config.ignore_patterns import BUILTIN_IGNORE_PATTERNS  # noqa: F401
from src.core.config.ignore_patterns import load_ignore_patterns      # noqa: F401
from src.core.config.ignore_patterns import is_ignored                # noqa: F401
from src.core.utils.vcs import (
    detect_vcs_type,                   # noqa: F401
    extract_vcs_metadata,              # noqa: F401
    extract_git_metadata,              # noqa: F401
    extract_svn_metadata,              # noqa: F401
    get_remote_url,                    # noqa: F401
    normalize_remote_url as _normalize_remote_url,
    parse_repo_name_from_url,          # noqa: F401
    get_inferred_repo_name,            # noqa: F401
    get_canonical_repo_root,           # noqa: F401
    is_git_repo,                       # noqa: F401
    has_git_dir,                       # noqa: F401
    get_current_commit,                # noqa: F401
    ensure_codecortex_ignored,         # noqa: F401
    get_changed_files,                 # noqa: F401
)

logger = logging.getLogger("CodeCortex.CodeRepository.Utils")

STORAGE_DIR = ".codecortex"

SECRETS_PATTERNS = [
    (re.compile(r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.I), "api_key"),
    (re.compile(r'(?:secret|token|password|passwd)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.I), "password_or_token"),
    (re.compile(r'(?:-----BEGIN\s+(?:RSA|OPENSSH|EC)\s+PRIVATE\s+KEY-----)', re.I), "private_key"),
    (re.compile(r'(?:ghp_|gho_|github_pat_)[a-zA-Z0-9]{36,}', re.I), "github_token"),
    (re.compile(r'(?:sk-[a-zA-Z0-9]{32,})', re.I), "openai_api_key"),
    (re.compile(r'(?:AKIA[0-9A-Z]{16})', re.I), "aws_access_key"),
]

def scan_secrets(path: str, exclude_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Scan files for potential secrets."""
    findings = []
    exclude = set(exclude_paths or [])
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if os.path.join(root, d) not in exclude]
        for fname in files:
            fpath = os.path.join(root, fname)
            if any(fpath.startswith(e) for e in exclude):
                continue
            try:
                with open(fpath, 'r', errors='ignore') as f:
                    content = f.read()
                for pattern, secret_type in SECRETS_PATTERNS:
                    if pattern.search(content):
                        findings.append({"file": fpath, "type": secret_type})
            except Exception:
                pass
    return findings

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
# 5. SIBLING CLONE DETECTION
# ═══════════════════════════════════════════════════════════════════

def find_sibling_clones(
    remote_url: str,
    self_path: str,
    registry_entries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Find other registered entries that share the same remote URL (sibling clones)."""
    if not remote_url:
        return []
    self_normalized = canonicalize_path(self_path)
    return [
        e for e in registry_entries
        if e.get("remote_url") == remote_url
        and canonicalize_path(e.get("path", "")) != self_normalized
    ]

def check_staleness_against_head(
    repo_path: str, last_commit: Optional[str],
) -> Dict[str, Any]:
    """Check if the index is behind HEAD."""
    import subprocess
    if not last_commit:
        return {"is_stale": False, "commits_behind": 0}
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{last_commit}..HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            behind = int(result.stdout.strip() or "0")
            return {
                "is_stale": behind > 0,
                "commits_behind": behind,
                "hint": f"Index is {behind} commit(s) behind HEAD" if behind > 0 else "Up to date",
            }
    except Exception:
        pass
    return {"is_stale": False, "commits_behind": 0}

# ═══════════════════════════════════════════════════════════════════
# 6. REGISTRY METADATA ENHANCEMENT
# ═══════════════════════════════════════════════════════════════════

def build_registry_meta(
    repo_path: str,
    stats: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Build enhanced registry metadata entry."""
    return {
        "path": canonicalize_path(repo_path),
        "last_commit": get_current_commit(repo_path),
        "remote_url": get_remote_url(repo_path),
        "repo_name": get_inferred_repo_name(repo_path) or Path(repo_path).name,
        "stats": stats or {},
    }
