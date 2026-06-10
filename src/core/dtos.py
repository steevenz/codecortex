"""
Shared domain DTOs — cross-module data transfer objects.

:project: CodeCortex
:package: Core.Dtos
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class VcsInfo:
    """VCS metadata for a repository snapshot.

    Used by: codeanalysis, coderepository, filesystem.
    """
    vcs_type: str = "none"
    branch: Optional[str] = None
    commit: Optional[str] = None
    commit_date: Optional[str] = None
    remote_url: Optional[str] = None
    added: int = 0
    modified: int = 0
    deleted: int = 0

@dataclass
class MetricsInfo:
    """Codebase metrics summary.

    Used by: codeanalysis, coderepository, codegraph.
    """
    total_files: int = 0
    total_directories: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    comment_ratio: float = 0.0
    languages: Dict[str, int] = field(default_factory=dict)

@dataclass
class GraphStatsInfo:
    """Knowledge graph statistics.

    Used by: codeanalysis, codegraph.
    """
    total_nodes: int = 0
    total_edges: int = 0
    density: float = 0.0
    components: int = 0
    relationship_types: Dict[str, int] = field(default_factory=dict)

@dataclass
class FileStats:
    """File-level statistics."""
    total_files: int = 0
    total_size_mb: float = 0.0
    avg_size_kb: float = 0.0
    source_code_files: int = 0
    config_files: int = 0
    documentation: int = 0
    binaries: int = 0
    others: int = 0
    largest_files: List[Dict[str, Any]] = field(default_factory=list)
