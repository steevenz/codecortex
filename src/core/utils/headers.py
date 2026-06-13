"""
Core utilities — file header generation and banner comment creation.

:project: CodeCortex
:package: Core.Utils.Headers
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Standard file header formats per coding-standard.md / project-structure-standard.md §4.1
# ---------------------------------------------------------------------------

FILE_HEADER_FORMATS: dict[str, str] = {
    "python": (
        '"""\n'
        "@project   {project_name}\n"
        "@package   {package_path}\n"
        "@author    {author}\n"
        "@copyright (c) {author}\n"
        "@fileoverview {description}\n"
        '"""\n'
    ),
    "typescript": (
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "php": (
        "<?php\n"
        "/**\n"
        " * @project   {project_name}\n"
        " * @package   {package_path}\n"
        " * @author    {author}\n"
        " * @copyright (c) {author}\n"
        " * @fileoverview {description}\n"
        " */\n"
    ),
    "go": (
        "// Package {package_name} — {description}\n"
        "//\n"
        "// Copyright (c) {author}\n"
    ),
    "kotlin": (
        "/**\n"
        " * Project: {project_name}\n"
        " * Package: {package_path}\n"
        " * Author: {author}\n"
        " * Copyright (c) {author}\n"
        " * File overview: {description}\n"
        " */\n"
    ),
    "shell": (
        "#!/bin/bash\n"
        "# @project   {project_name}\n"
        "# @category  {package_path}\n"
        "# @author    {author}\n"
        "# @copyright (c) {author}\n"
        "# @fileoverview {description}\n"
    ),
}

_EXTENSION_TO_STACK: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".php": "php",
    ".go": "go",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".sh": "shell",
    ".bash": "shell",
    ".bat": "shell",
    ".ps1": "shell",
}

class FileHeader:
    """Generates file headers compliant with standard coding conventions.

    Each language/stack has a specific header format defined in ``FILE_HEADER_FORMATS``.
    Stack manifests can override the default format via ``header_format``.
    """

    def __init__(self, custom_formats: Optional[dict[str, str]] = None) -> None:
        self._formats: dict[str, str] = {**FILE_HEADER_FORMATS}
        if custom_formats:
            self._formats.update(custom_formats)

    def generate(
        self,
        *,
        file_path: str,
        project_name: str,
        package_path: str,
        author: str,
        description: str,
        stack_name: Optional[str] = None,
    ) -> str:
        resolved_stack = stack_name or self._detect_stack(file_path)
        if resolved_stack is None:
            return ""

        fmt = self._formats.get(resolved_stack)
        if fmt is None:
            return ""

        package_name = package_path.rsplit(".", 1)[-1] if "." in package_path else package_path.rsplit("/", 1)[-1]

        return fmt.format(
            project_name=project_name,
            package_path=package_path,
            package_name=package_name,
            author=author,
            description=description,
        )

    def generate_for_init(
        self,
        *,
        project_name: str,
        package_path: str,
        author: str,
        stack_name: str = "python",
    ) -> str:
        return self.generate(
            file_path="__init__.py",
            project_name=project_name,
            package_path=package_path,
            author=author,
            description=f"Package initialiser for {package_path}.",
            stack_name=stack_name,
        )

    @staticmethod
    def _detect_stack(file_path: str) -> Optional[str]:
        ext = Path(file_path).suffix.lower()
        return _EXTENSION_TO_STACK.get(ext)

def banner(path: Path, author: str, filename: str, project_name: str) -> str:
    """Return a standard docstring-style header comment for a new file."""
    import textwrap
    rel = f"{project_name}/{path.relative_to(path.anchor)}" if path.is_absolute() else f"{project_name}/{path}"
    creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return textwrap.dedent(f'''"""\n    {rel}\n    Author: {author}\n    Created: {creation_date}\n    Description: Part of {project_name} project\n    """''').strip()
