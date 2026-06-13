"""
Filesystem — safe file and directory operations for scaffolding output.

:project: CodeCortex
:package: Modules.Scaffolder.Adapters.Filesystem
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Filesystem:
    """Safe filesystem operations for project scaffolding."""

    @staticmethod
    def ensure_directory(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def directory_exists(path: Path) -> bool:
        return path.is_dir()

    @staticmethod
    def remove_directory(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)
            logger.info("Removed directory: %s", path)

    @staticmethod
    def write(path: Path, content: str, *, encoding: str = "utf-8", progress_callback=None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        if progress_callback:
            progress_callback(f"Created file: {path}")

    @staticmethod
    def read(path: Path, *, encoding: str = "utf-8") -> str:
        return path.read_text(encoding=encoding)

    @staticmethod
    def exists(path: Path) -> bool:
        return path.is_file()

    @staticmethod
    def set_executable(path: Path) -> None:
        try:
            current = path.stat().st_mode
            path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass

    @staticmethod
    def copy(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    @staticmethod
    def copy_tree(source: Path, destination: Path) -> None:
        shutil.copytree(source, destination, dirs_exist_ok=True)

