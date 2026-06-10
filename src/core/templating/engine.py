"""
Core templating — Jinja2-based template rendering engine.

:project: CodeCortex
:package: Core.Templating.Engine
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateNotFound,
    select_autoescape,
)

class TemplateNotFoundError(LookupError):
    """Raised when a template file cannot be resolved."""

    def __init__(self, template_path: str) -> None:
        self.template_path = template_path
        super().__init__(f"Template not found: {template_path}")

class TemplateRenderError(RuntimeError):
    """Raised when Jinja2 template rendering fails."""

    def __init__(self, template_name: str, detail: str) -> None:
        self.template_name = template_name
        self.detail = detail
        super().__init__(f"Failed to render template '{template_name}': {detail}")

class Engine:
    """Renders Jinja2 templates with a pre-configured environment.

    The engine is initialised with one or more filesystem search paths
    and provides custom filters useful for code generation.
    """

    def __init__(self, templates_root: Path) -> None:
        self._templates_root = templates_root
        self._env = self._build_environment(templates_root)

    def render_template(self, source_path: str, variables: dict[str, Any]) -> str:
        """Render a template file to a string.

        Args:
            source_path: Relative path inside the templates root.
            variables:   Context variables passed to Jinja2.

        Returns:
            Rendered content as a string.

        Raises:
            TemplateNotFoundError: If the source template does not exist.
            TemplateRenderError: If Jinja2 rendering fails.
        """
        try:
            jinja_template = self._env.get_template(source_path)
        except TemplateNotFound:
            raise TemplateNotFoundError(source_path)

        try:
            return jinja_template.render(**variables)
        except Exception as exc:
            raise TemplateRenderError(source_path, str(exc)) from exc

    def render_string(self, template_string: str, variables: dict[str, Any]) -> str:
        """Render an inline template string (e.g. header format from manifest).

        Args:
            template_string: Raw Jinja2 template string.
            variables:       Context variables.

        Returns:
            Rendered string.

        Raises:
            TemplateRenderError: If rendering fails.
        """
        try:
            tmpl = self._env.from_string(template_string)
            return tmpl.render(**variables)
        except Exception as exc:
            raise TemplateRenderError("<inline>", str(exc)) from exc

    def template_exists(self, source_path: str) -> bool:
        """Check whether a template file exists in the search paths."""
        try:
            self._env.get_template(source_path)
            return True
        except TemplateNotFound:
            return False

    def _build_environment(self, templates_root: Path) -> Environment:
        """Build a Jinja2 environment with custom settings and filters."""
        loader = FileSystemLoader(
            searchpath=[str(templates_root)],
            encoding="utf-8",
            followlinks=True,
        )

        env = Environment(
            loader=loader,
            autoescape=select_autoescape(default=False, default_for_string=False),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        env.filters["snake_case"] = self._filter_snake_case
        env.filters["kebab_case"] = self._filter_kebab_case
        env.filters["pascal_case"] = self._filter_pascal_case
        env.filters["camel_case"] = self._filter_camel_case
        env.filters["indent_lines"] = self._filter_indent_lines
        env.filters["quote"] = self._filter_quote

        return env

    # ------------------------------------------------------------------
    # Custom Jinja2 filters
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_snake_case(value: str) -> str:
        import re
        s = re.sub(r"[^a-zA-Z0-9]", "_", value)
        s = re.sub(r"_+", "_", s)
        return s.strip("_").lower()

    @staticmethod
    def _filter_kebab_case(value: str) -> str:
        import re
        s = re.sub(r"[^a-zA-Z0-9]", "-", value)
        s = re.sub(r"-+", "-", s)
        return s.strip("-").lower()

    @staticmethod
    def _filter_pascal_case(value: str) -> str:
        import re
        words = re.split(r"[^a-zA-Z0-9]", value)
        return "".join(w.capitalize() for w in words if w)

    @staticmethod
    def _filter_camel_case(value: str) -> str:
        import re
        words = re.split(r"[^a-zA-Z0-9]", value)
        if not words:
            return ""
        return words[0].lower() + "".join(w.capitalize() for w in words[1:] if w)

    @staticmethod
    def _filter_indent_lines(value: str, width: int = 4) -> str:
        prefix = " " * width
        return "\n".join(prefix + line if line.strip() else line for line in value.splitlines())

    @staticmethod
    def _filter_quote(value: str) -> str:
        return f'"{value}"'
