"""
Data-transfer objects / domain entities for the scaffolding module.

:project: CodeCortex
:package: Modules.Scaffolder.Core.Dtos
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .constants import FileConvention, ProjectPattern, StackType
from .license import License
from .name import Name
from src.core import Version

@dataclass
class ProjectType:
    """A project type available within a specific stack (e.g. ``web_api`` in Python).

    Loaded from the stack's ``manifest.yml``.
    """

    id: str
    display_name: str
    description: str = ""
    pattern: ProjectPattern = ProjectPattern.LAYERED
    dependencies: list[str] = field(default_factory=list)
    extra_directories: list[str] = field(default_factory=list)
    conditional_modules: dict[str, bool] = field(default_factory=dict)

@dataclass
class FileConventions:
    """Naming conventions for files and directories within a stack."""

    directories: FileConvention = FileConvention.SNAKE_CASE
    modules: str = "snake_case.py"
    classes: str = "PascalCase"

@dataclass
class Stack:
    """Represents a registered technology stack (e.g. Python, TypeScript, Go).

    Each stack is backed by a ``manifest.yml`` in ``datasets/templates/{name}/``
    and contains one or more ``ProjectType`` entries.
    """

    name: str
    display_name: str
    version: str = ""
    file_conventions: FileConventions = field(default_factory=FileConventions)
    project_types: list[ProjectType] = field(default_factory=list)
    template_files_base: list[str] = field(default_factory=list)
    template_files_setup: list[str] = field(default_factory=list)
    header_format: str = ""
    templates_path: Optional[str] = None

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_project_type(self, type_id: str) -> Optional[ProjectType]:
        """Resolve a project type by its identifier."""
        for pt in self.project_types:
            if pt.id == type_id:
                return pt
        return None

    @property
    def project_type_ids(self) -> list[str]:
        return [pt.id for pt in self.project_types]

    @property
    def stack_type(self) -> Optional[StackType]:
        """Map the stack name to a ``StackType`` enum, if registered."""
        try:
            return StackType(self.name)
        except ValueError:
            return None

@dataclass
class Project:
    """Aggregate root representing a project to be scaffolded.

    Holds all user choices and derived data required by the scaffold pipeline.
    """

    name: Name
    target_path: Path
    stack_name: str
    project_type: ProjectType
    author: str
    email: str
    version: Version = field(default_factory=Version.default)
    license: License = field(default_factory=License.none)
    include_ai: bool = False
    include_trainer: bool = False
    project_code: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # ------------------------------------------------------------------
    # Template context
    # ------------------------------------------------------------------

    def template_context(self) -> dict[str, Any]:
        """Build the full Jinja2 context dictionary for template rendering."""
        return {
            # Project identity
            "project_name": self.name.display,
            "project_slug": self.name.slug,
            "project_snake": self.name.snake,
            "project_pascal": self.name.pascal,
            "project_code": self.project_code or "",
            "project_version": str(self.version),
            "project_directory": self.target_path.name,

            # Author
            "author": self.author,
            "email": self.email,
            "year": self.created_at.year,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),

            # Stack & type
            "stack_name": self.stack_name,
            "project_type_id": self.project_type.id,
            "project_type_name": self.project_type.display_name,
            "project_pattern": self.project_type.pattern.value,

            # Options
            "include_ai": self.include_ai,
            "include_trainer": self.include_trainer,

            # License
            "license_name": str(self.license),
            "has_license": not self.license.is_none,

            # Dependencies
            "dependencies": self.project_type.dependencies,
            "extra_directories": self.project_type.extra_directories,
        }

@dataclass
class Template:
    """A single renderable template that maps to one output file in the generated project.

    Attributes:
        source_path:   Relative path inside the templates directory (e.g. ``python/src/main.py.j2``).
        target_path:   Relative path in the generated project (e.g. ``src/main.py``).
        variables:     Context variables passed to the Jinja2 renderer.
        executable:    Whether the output file should be marked as executable (e.g. setup scripts).
        skip_if_exists: Do not overwrite if the target already exists.
    """

    source_path: str
    target_path: str
    variables: dict[str, Any] = field(default_factory=dict)
    executable: bool = False
    skip_if_exists: bool = False

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def source(self) -> Path:
        return Path(self.source_path)

    @property
    def target(self) -> Path:
        return Path(self.target_path)

    @property
    def target_extension(self) -> str:
        """Return the target file extension (without the ``.j2`` suffix)."""
        return self.target.suffix

    def with_variables(self, extra: dict[str, Any]) -> Template:
        """Return a copy with merged variables."""
        merged = {**self.variables, **extra}
        return Template(
            source_path=self.source_path,
            target_path=self.target_path,
            variables=merged,
            executable=self.executable,
            skip_if_exists=self.skip_if_exists,
        )
