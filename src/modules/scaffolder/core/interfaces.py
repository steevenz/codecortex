"""
Abstract interfaces for stack and template repositories.

:project: CodeCortex
:package: Modules.Scaffolder.Core.Interfaces
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .dtos import Stack, Template

class StackRepository(ABC):
    """Interface for discovering and loading registered technology stacks.

    Each stack is defined by a ``manifest.yml`` in ``datasets/templates/{stack_name}/``.
    Implementations discover available stacks and parse their manifests into
    ``Stack`` entities.
    """

    @abstractmethod
    def list_stacks(self) -> list[Stack]:
        """Return all discovered stacks.

        Returns:
            List of ``Stack`` entities, one per valid manifest found.
        """

    @abstractmethod
    def get_stack(self, name: str) -> Optional[Stack]:
        """Return a single stack by name.

        Args:
            name: Stack identifier (e.g. ``python``, ``typescript``).

        Returns:
            ``Stack`` entity, or ``None`` if not found.
        """

    @abstractmethod
    def stack_exists(self, name: str) -> bool:
        """Check whether a stack with the given name is registered."""

    @abstractmethod
    def reload(self) -> None:
        """Re-scan the templates directory and reload all manifests.

        Useful after adding a new stack folder at runtime.
        """

class TemplateRepository(ABC):
    """Interface for resolving and reading template files.

    Implementations may read from a local filesystem, a remote Git repo,
    or a package registry.
    """

    @abstractmethod
    def get_shared_templates(self) -> list[Template]:
        """Return all templates from the ``_shared/`` directory.

        These are stack-agnostic files such as ``.gitignore``, ``README.md``,
        ``LICENSE``, ``.version``, and the ``docs/`` scaffolding.
        """

    @abstractmethod
    def get_stack_templates(self, stack_name: str, project_type_id: str) -> list[Template]:
        """Return all templates for a specific stack and project type.

        Args:
            stack_name: Stack identifier (e.g. ``python``, ``typescript``).
            project_type_id: Project type identifier (e.g. ``standard``, ``web_api``).

        Returns:
            Ordered list of templates to render.
        """

    @abstractmethod
    def read_template_content(self, template_path: str) -> str:
        """Read raw Jinja2 template content from the given path.

        Args:
            template_path: Relative path within the templates directory.

        Returns:
            Raw template string.

        Raises:
            TemplateNotFoundError: If the file does not exist.
        """

    @abstractmethod
    def template_exists(self, template_path: str) -> bool:
        """Check whether a template file exists at the given path."""

    @abstractmethod
    def get_templates_root(self) -> Path:
        """Return the absolute path to the templates root directory."""
