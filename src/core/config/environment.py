"""
Environment configuration utilities.
Provides version information and environment variable handling.

:project: CodeCortex
:package: Core.Config.Environment
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

class VersionProvider:
    """
    Provides version information without global state.

    Follows Aegis modular-standard.md requirement for no global state.
    Version caching is handled internally within the instance.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or Path(__file__).resolve().parents[3]
        self._cache: Optional[str] = None

    def get_version(self) -> str:
        """
        Load and cache version from .version file.

        Returns:
            Version string or "0.0.0" if file not found
        """
        if self._cache is not None:
            return self._cache

        version_path = self._project_root / ".version"
        try:
            self._cache = version_path.read_text(encoding="utf-8").strip()
        except Exception:
            self._cache = "0.0.0"
        return self._cache

def load_version(project_root: Optional[Path] = None) -> str:
    """
    Load version using provider pattern (no global state).
    Each call creates a fresh provider; cached internally per instance.
    """
    return VersionProvider(project_root).get_version()

def new_request_id() -> str:
    return f"req_{uuid4()}"

def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    v = raw.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def utc_ts_to_iso(ts: float) -> str:
    """Convert a Unix timestamp (seconds or milliseconds) to ISO 8601 UTC string.

    Args:
        ts: Unix timestamp. Values > 1e12 are treated as milliseconds.

    Returns:
        ISO 8601 string with UTC ``Z`` suffix.
    """
    if ts > 1e12:
        ts = ts / 1000.0
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
