"""
Custom exceptions for the PyScaffold generator engine.

:project: CodeCortex
:package: Modules.Scaffolder.Core.Exceptions
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""

from __future__ import annotations

class PyScaffoldError(Exception):
    """Base exception for all PyScaffold errors."""

# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------

class ValidationError(PyScaffoldError):
    """Raised when input validation fails."""

class InvalidNameError(ValidationError):
    """Raised when a project name does not meet naming conventions."""

    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason
        super().__init__(f"Invalid project name '{name}': {reason}")

class InvalidVersionError(ValidationError):
    """Raised when a version string does not conform to Semantic Versioning 2.0.0."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(
            f"Invalid version '{version}': must follow MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]"
        )

class UnsupportedTargetLanguageError(ValidationError):
    """Raised when a requested target language/stack is not supported."""

    def __init__(self, target: str, supported: list[str]) -> None:
        self.target = target
        self.supported = supported
        super().__init__(f"Unsupported target '{target}'. Supported: {', '.join(supported)}")

class UnsupportedFrameworkError(ValidationError):
    """Raised when a requested framework is not supported for the selected stack."""

    def __init__(self, stack: str, framework: str, supported: list[str]) -> None:
        self.stack = stack
        self.framework = framework
        self.supported = supported
        super().__init__(
            f"Unsupported framework '{framework}' for stack '{stack}'. Supported: {', '.join(supported)}"
        )

# ---------------------------------------------------------------------------
# Stack / Template Errors
# ---------------------------------------------------------------------------

class StackNotFoundError(PyScaffoldError):
    """Raised when a requested stack is not registered in the template registry."""

    def __init__(self, stack_name: str) -> None:
        self.stack_name = stack_name
        super().__init__(f"Stack '{stack_name}' not found in template registry")

class TemplateNotFoundError(PyScaffoldError):
    """Raised when a template file cannot be resolved."""

    def __init__(self, template_path: str) -> None:
        self.template_path = template_path
        super().__init__(f"Template not found: {template_path}")

class ManifestParseError(PyScaffoldError):
    """Raised when a stack manifest.yml is malformed or missing required fields."""

    def __init__(self, manifest_path: str, detail: str) -> None:
        self.manifest_path = manifest_path
        self.detail = detail
        super().__init__(f"Failed to parse manifest '{manifest_path}': {detail}")

# ---------------------------------------------------------------------------
# Scaffold Errors
# ---------------------------------------------------------------------------

class ScaffoldError(PyScaffoldError):
    """Raised when project scaffolding fails."""

class ProjectAlreadyExistsError(ScaffoldError):
    """Raised when the target project directory already exists."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Project directory already exists: {path}")

class TemplateRenderError(ScaffoldError):
    """Raised when Jinja2 template rendering fails."""

    def __init__(self, template_name: str, detail: str) -> None:
        self.template_name = template_name
        self.detail = detail
        super().__init__(f"Failed to render template '{template_name}': {detail}")

# ---------------------------------------------------------------------------
# Configuration Errors
# ---------------------------------------------------------------------------

class ConfigurationError(PyScaffoldError):
    """Raised when configuration loading or validation fails."""
