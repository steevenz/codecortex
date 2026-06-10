"""
Adapter layer for the scaffolding module.

:project: CodeCortex
:package: Modules.Scaffolder.Adapters
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Scaffolder-v1.0
"""
from .filesystem import Filesystem
from .git import Git
from .stack import Stack
from .template import Template

__all__ = [
    "Filesystem",
    "Git",
    "Stack",
    "Template",
]
