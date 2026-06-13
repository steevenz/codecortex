"""
Backward-compatible shim — delegates to services/cli.py.

:project: CodeCortex
:package: Modules.Scaffolder.Main
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

from __future__ import annotations

from .services.cli import (
    CLI as CLIService,
    run_cli,
    main,
    ensure_agents_skills_links,
    find_syc_concept_path,
    parse_syc_concept_markdown,
)

__all__ = [
    "CLIService",
    "run_cli",
    "main",
    "ensure_agents_skills_links",
    "find_syc_concept_path",
    "parse_syc_concept_markdown",
]
