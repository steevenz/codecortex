"""
Template — resolves Jinja2 templates from local disk.

:project: CodeCortex
:package: Modules.Scaffolder.Adapters.Template
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..core.constants import SHARED_TEMPLATES_DIR
from ..core.exceptions import TemplateNotFoundError
from ..core.dtos import Template
from ..core.interfaces import TemplateRepository

logger = logging.getLogger(__name__)

_EXECUTABLE_EXTENSIONS = {".sh", ".bash"}

class TemplateAdapter(TemplateRepository):
    """Resolves Jinja2 template files from the local filesystem."""

    def __init__(self, templates_root: Path) -> None:
        self._root = templates_root

    def get_shared_templates(self) -> list[Template]:
        shared_dir = self._root / SHARED_TEMPLATES_DIR
        if not shared_dir.exists():
            logger.warning("Shared templates directory not found: %s", shared_dir)
            return []
        return self._scan_directory(shared_dir, prefix=SHARED_TEMPLATES_DIR)

    def get_stack_templates(self, stack_name: str, project_type_id: str) -> list[Template]:
        stack_dir = self._root / stack_name
        if not stack_dir.exists():
            logger.warning("Stack templates directory not found: %s", stack_dir)
            return []

        templates: list[Template] = []
        templates.extend(self._scan_directory(stack_dir, prefix=stack_name, exclude={"manifest.yml"}))

        type_dir = stack_dir / "types" / project_type_id
        if type_dir.exists():
            templates.extend(self._scan_directory(type_dir, prefix=f"{stack_name}/types/{project_type_id}"))

        return templates

    def read_template_content(self, template_path: str) -> str:
        full_path = self._root / template_path
        if not full_path.exists():
            raise TemplateNotFoundError(template_path)
        return full_path.read_text(encoding="utf-8")

    def template_exists(self, template_path: str) -> bool:
        return (self._root / template_path).exists()

    def get_templates_root(self) -> Path:
        return self._root

    def _scan_directory(
        self,
        directory: Path,
        prefix: str,
        exclude: Optional[set[str]] = None,
    ) -> list[Template]:
        exclude = exclude or set()
        templates: list[Template] = []

        for file_path in sorted(directory.rglob("*.j2")):
            if file_path.name in exclude:
                continue

            source_path = str(file_path.relative_to(self._root)).replace("\\", "/")

            rel_to_stack = file_path.relative_to(directory)
            target_path = str(rel_to_stack).replace("\\", "/")
            if target_path.endswith(".j2"):
                target_path = target_path[:-3]

            executable = Path(target_path).suffix.lower() in _EXECUTABLE_EXTENSIONS

            templates.append(Template(
                source_path=source_path,
                target_path=target_path,
                executable=executable,
            ))

        return templates
