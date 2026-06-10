"""
Name value object — validates and normalises project naming across conventions.

:project: CodeCortex
:package: Modules.Scaffolder.Core.Name
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .exceptions import InvalidNameError

@dataclass(frozen=True)
class Name:
    """Immutable value object representing a validated project name.

    Provides derived forms used throughout scaffolding:
    - ``display``   : Human-readable title (Title Case)
    - ``slug``      : URL / directory-safe kebab-case
    - ``snake``     : Python package-safe snake_case
    - ``pascal``    : PascalCase class prefix
    """

    display: str
    slug: str
    snake: str
    pascal: str

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, raw: str) -> Name:
        """Create a ``Name`` from arbitrary user input.

        Args:
            raw: Free-form project name string.

        Returns:
            Validated ``Name`` instance.

        Raises:
            InvalidNameError: If the input cannot be normalised.
        """
        cleaned = raw.strip()
        if not cleaned:
            raise InvalidNameError(raw, "Project name cannot be empty")

        if len(cleaned) < 2:
            raise InvalidNameError(raw, "Project name must be at least 2 characters")

        # Reject names that are only special characters
        if not re.search(r"[a-zA-Z0-9]", cleaned):
            raise InvalidNameError(raw, "Project name must contain alphanumeric characters")

        display = cls._to_title(cleaned)
        slug = cls._to_slug(cleaned)
        snake = cls._to_snake(cleaned)
        pascal = cls._to_pascal(cleaned)

        # Final guard — snake must be a valid Python identifier
        if not snake.isidentifier():
            raise InvalidNameError(raw, f"Derived snake_case '{snake}' is not a valid identifier")

        return cls(display=display, slug=slug, snake=snake, pascal=pascal)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_title(value: str) -> str:
        return value.title()

    @staticmethod
    def _to_slug(value: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9\s\-_]", "", value.lower())
        s = re.sub(r"[\s_]+", "-", s.strip())
        return re.sub(r"-+", "-", s).strip("-")

    @staticmethod
    def _to_snake(value: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9\s\-_]", "", value.lower())
        s = re.sub(r"[\s\-]+", "_", s.strip())
        return re.sub(r"_+", "_", s).strip("_")

    @staticmethod
    def _to_pascal(value: str) -> str:
        words = re.split(r"[\s\-_]+", value.strip())
        return "".join(w.capitalize() for w in words if w)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __str__(self) -> str:  # noqa: D105
        return self.display
