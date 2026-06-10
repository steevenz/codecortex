"""
OS-level utilities — user/group resolution from stat info.

:project: CodeCortex
:package: Core.Utils.System
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import os

try:
    import pwd
except ImportError:
    pwd = None  # type: ignore[assignment]

try:
    import grp
except ImportError:
    grp = None  # type: ignore[assignment]

def get_owner(uid: int) -> str:
    """Resolve a Unix UID to a human-readable username."""
    try:
        if pwd is not None:
            return pwd.getpwuid(uid).pw_name
    except (KeyError, OSError):
        pass
    return str(uid)

def get_group(gid: int) -> str:
    """Resolve a Unix GID to a human-readable group name."""
    try:
        if grp is not None:
            return grp.getgrgid(gid).gr_name
    except (KeyError, OSError):
        pass
    return str(gid)

def get_username() -> str:
    """Get the current username in a cross-platform way."""
    try:
        if pwd is not None:
            return pwd.getpwuid(os.getuid()).pw_name
    except (KeyError, AttributeError):
        pass
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
