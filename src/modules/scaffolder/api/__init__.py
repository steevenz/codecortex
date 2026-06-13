"""
Scaffolder API package — MCP tool entry point.

:project: CodeCortex
:package: Modules.Scaffolder.Api
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""
from .tools import register_tools

__all__ = ["register_tools"]
