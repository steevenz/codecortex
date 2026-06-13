"""
Pydantic-based settings for PyScaffold.

:project: CodeCortex
:package: Modules.Scaffolder.Core.Config
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class AuthorSettings(BaseSettings):
    """Author defaults (overridden by git config when available)."""
    name: str = "Your Name"
    email: str = "your.email@example.com"

class LoggingSettings(BaseSettings):
    """Logging configuration."""
    level: str = "INFO"
    json_format: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "outputs/logs/pyscaffold.log"

class DockerSettings(BaseSettings):
    """Docker defaults for generated projects."""
    python_version: str = "3.12"
    base_image: str = "python:3.12-slim"
    workdir: str = "/app"
    port: int = 8000

class GitSettings(BaseSettings):
    """Git configuration for generated projects."""
    auto_init: bool = True
    ignore_patterns: list[str] = Field(default_factory=list)

class TestingSettings(BaseSettings):
    """Testing configuration for generated projects."""
    framework: str = "pytest"
    dependencies: list[str] = Field(default_factory=list)

class PyScaffold(BaseSettings):
    """Root settings for the PyScaffold generator engine.

    Loaded from environment variables with ``PYSCAFFOLD_`` prefix, or from
    the ``config/config.yml`` via manual injection.
    """

    model_config = {"env_prefix": "PYSCAFFOLD_"}

    # Paths (resolved relative to project root)
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    templates_dir: str = "datasets/templates"
    output_dir: str = "outputs/projects"

    # Defaults
    default_stack: str = "python"
    default_project_type: str = "standard"
    default_license: str = "MIT"
    default_include_ai: bool = False
    default_include_trainer: bool = False
    default_use_boilerplate: bool = False

    # Templates
    templates_base_files: list[str] = Field(default_factory=list)
    templates_setup_scripts: list[str] = Field(default_factory=list)

    # Structure
    structure_base_folders: list[str] = Field(default_factory=list)
    structure_conditional_folders: dict[str, list[str]] = Field(default_factory=dict)

    # Dependencies
    dependencies: dict[str, list[str]] = Field(default_factory=dict)

    # UI
    ui_default_mode: str = "cli"

    # Boilerplate
    boilerplate_templates_dir: str = "templates"
    boilerplate_available: list[str] = Field(default_factory=list)

    # Supported targets
    supported_targets: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Sub-settings
    author: AuthorSettings = Field(default_factory=AuthorSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    docker: DockerSettings = Field(default_factory=DockerSettings)
    git: GitSettings = Field(default_factory=GitSettings)
    testing: TestingSettings = Field(default_factory=TestingSettings)

    # ------------------------------------------------------------------
    # Derived paths
    # ------------------------------------------------------------------

    @property
    def templates_path(self) -> Path:
        """Absolute path to the templates directory."""
        return self.project_root / self.templates_dir

    @property
    def default_output_path(self) -> Path:
        """Absolute path to the default output directory."""
        return self.project_root / self.output_dir

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("default_stack")
    @classmethod
    def _validate_stack(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("default_project_type")
    @classmethod
    def _validate_project_type(cls, v: str) -> str:
        return v.strip().lower()

# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_settings: Optional[PyScaffold] = None

def get_settings() -> PyScaffold:
    """Return the global ``PyScaffold`` settings singleton.

    Call ``reset_settings()`` if you need to reload after environment changes.
    """
    global _settings
    if _settings is None:
        _settings = PyScaffold()
    return _settings

def reset_settings() -> None:
    """Force re-initialisation of the settings singleton."""
    global _settings
    _settings = None

# ---------------------------------------------------------------------------
# Backward-compatible ConfigManager (wraps PyScaffold settings)
# ---------------------------------------------------------------------------

class ConfigManager:
    """Thin wrapper around ``PyScaffold`` settings for backward compatibility."""

    def __init__(self, settings: Optional[PyScaffold] = None) -> None:
        self._settings = settings or get_settings()

    def list_supported_targets(self) -> dict[str, dict[str, Any]]:
        return dict(self._settings.supported_targets)

    def list_supported_active_targets(self) -> list[str]:
        return [
            name for name, meta in self._settings.supported_targets.items()
            if meta.get("status") != "disabled"
        ]

    def validate_target_language(self, target: str) -> str:
        from .exceptions import UnsupportedTargetLanguageError
        key = target.strip().lower()
        if key in self._settings.supported_targets:
            return key
        raise UnsupportedTargetLanguageError(target, list(self._settings.supported_targets.keys()))

_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
