"""
Git — wraps Git CLI operations for project initialisation.

:project: CodeCortex
:package: Modules.Scaffolder.Adapters.Git
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Git:
    """Thin wrapper around the ``git`` CLI."""

    @staticmethod
    def user() -> dict[str, Optional[str]]:
        return {
            "name": Git._git_config("user.name"),
            "email": Git._git_config("user.email"),
        }

    @staticmethod
    def get_user_name() -> Optional[str]:
        return Git._git_config("user.name")

    @staticmethod
    def get_user_email() -> Optional[str]:
        return Git._git_config("user.email")

    @staticmethod
    def init_repository(path: Path) -> bool:
        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(path),
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Initialised git repository in %s", path)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("git init failed in %s: %s", path, exc)
            return False

    @staticmethod
    def _git_config(key: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "config", key],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
