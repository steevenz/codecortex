"""
src/__init__.py
PyScaffold main package.

:project: CodeCortex
:package: Modules.Scaffolder
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

__version__ = "3.0.0"
__author__ = "PyScaffold Team"
__description__ = "Ultimate Python Project Boilerplate Generator"

from .core.config import PyScaffold, get_settings, get_config_manager
from .main import run_cli

__all__ = [
    "PyScaffold",
    "get_settings",
    "get_config_manager",
    "run_cli",
    "__version__",
    "__author__",
    "__description__"
]
