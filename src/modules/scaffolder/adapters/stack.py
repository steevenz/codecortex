"""
Stack — discovers stacks by scanning manifest.yml files on disk.

:project: CodeCortex
:package: Modules.Scaffolder.Adapters.Stack
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from ..core.constants import FileConvention, ProjectPattern
from ..core.exceptions import ManifestParseError
from ..core.dtos import FileConventions, ProjectType
from ..core.dtos import Stack as StackDTO
from ..core.interfaces import StackRepository

logger = logging.getLogger(__name__)

class Stack(StackRepository):
    """Discovers stacks by scanning ``datasets/templates/*/manifest.yml``."""

    def __init__(self, templates_root: Path) -> None:
        self._root = templates_root
        self._stacks: dict[str, Stack] = {}
        self.reload()

    def list_stacks(self) -> list[Stack]:
        return list(self._stacks.values())

    def get_stack(self, name: str) -> Optional[Stack]:
        return self._stacks.get(name)

    def stack_exists(self, name: str) -> bool:
        return name in self._stacks

    def reload(self) -> None:
        self._stacks.clear()
        if not self._root.exists():
            logger.warning("Templates root does not exist: %s", self._root)
            return
        for child in sorted(self._root.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            manifest = child / "manifest.yml"
            if not manifest.exists():
                continue
            try:
                stack = self._parse_manifest(manifest, child)
                self._stacks[stack.name] = stack
                logger.info("Registered stack: %s (%d project types)",
                            stack.display_name, len(stack.project_types))
            except ManifestParseError as exc:
                logger.error("Failed to load stack '%s': %s", child.name, exc)

    def _parse_manifest(self, manifest_path: Path, stack_dir: Path) -> Stack:
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except Exception as exc:
            raise ManifestParseError(str(manifest_path), str(exc)) from exc
        if not isinstance(data, dict):
            raise ManifestParseError(str(manifest_path), "Root must be a mapping")
        stack_data = data.get("stack", {})
        if not stack_data.get("name"):
            raise ManifestParseError(str(manifest_path), "Missing stack.name")
        fc_data = stack_data.get("file_conventions", {})
        file_conventions = FileConventions(
            directories=FileConvention(fc_data.get("directories", "snake_case")),
            modules=fc_data.get("modules", "snake_case.py"),
            classes=fc_data.get("classes", "PascalCase"),
        )
        project_types: list[ProjectType] = []
        for pt_data in data.get("project_types", []):
            pt = ProjectType(
                id=pt_data["id"],
                display_name=pt_data.get("display_name", pt_data["id"]),
                description=pt_data.get("description", ""),
                pattern=ProjectPattern(pt_data.get("pattern", "layered")),
                dependencies=pt_data.get("dependencies", []),
                extra_directories=pt_data.get("extra_directories", []),
                conditional_modules=pt_data.get("conditional_modules", {}),
            )
            project_types.append(pt)
        tf_data = data.get("template_files", {})
        return StackDTO(
            name=stack_data["name"],
            display_name=stack_data.get("display_name", stack_data["name"].title()),
            version=stack_data.get("version", ""),
            file_conventions=file_conventions,
            project_types=project_types,
            template_files_base=tf_data.get("base", []),
            template_files_setup=tf_data.get("setup_scripts", []),
            header_format=data.get("header_format", ""),
            templates_path=str(stack_dir),
        )
