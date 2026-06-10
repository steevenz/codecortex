"""
Subprocess utilities — non-blocking version detection.

:project: CodeCortex
:package: Core.Utils.Process
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import subprocess
from typing import Optional

def try_get_version(workdir: str, cmd: str, timeout: int = 5) -> Optional[str]:
    """Execute a command to get framework version. Non-blocking.

    Args:
        workdir: Working directory for the subprocess.
        cmd: Command string (e.g. ``python --version``).
        timeout: Subprocess timeout in seconds.

    Returns:
        First 100 chars of stdout on success, or None on failure.
    """
    try:
        result = subprocess.run(
            cmd.split(),
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()[:100] if result.returncode == 0 else None
    except Exception:
        return None
