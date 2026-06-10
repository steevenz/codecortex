"""
Data Transfer Objects for CodeRefactor Domain.
Supports 12 actions: impact, rename, move, change_signature,
extract_function, inline_function, preview, apply,
rename_file, rename_folder, move_file, modularize.

:project: CodeCortex
:package: Modules.Coderefactor.Core.Dtos
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeRefactor-v1.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# Structured Error Codes — REF_<category>_<detail>
# ─────────────────────────────────────────────────────────────────────────────

class RefactorErrorCode:
    """Canonical error codes for CodeRefactor domain."""

    # 4xx — client / input errors
    INVALID_ACTION          = "REF_400_INVALID_ACTION"
    MISSING_REPO            = "REF_404_REPO_NOT_FOUND"
    MISSING_SYMBOL          = "REF_404_SYMBOL_NOT_FOUND"
    MISSING_SOURCE_FILE     = "REF_404_SOURCE_FILE_NOT_FOUND"
    MISSING_TARGET_FILE     = "REF_404_TARGET_FILE_NOT_FOUND"
    MISSING_PARAM           = "REF_400_MISSING_PARAM"
    INVALID_LINE_RANGE      = "REF_400_INVALID_LINE_RANGE"
    TARGET_ALREADY_EXISTS   = "REF_409_TARGET_EXISTS"
    UNSUPPORTED_LANGUAGE    = "REF_422_UNSUPPORTED_LANGUAGE"
    NO_SYMBOLS_FOUND        = "REF_422_NO_SYMBOLS_FOUND"
    NO_CALL_SITES           = "REF_422_NO_CALL_SITES"
    GRAPH_EMPTY             = "REF_412_GRAPH_EMPTY"

    # 5xx — server / runtime errors
    GIT_COMMIT_FAILED       = "REF_500_GIT_COMMIT_FAILED"
    REINDEX_FAILED          = "REF_500_REINDEX_FAILED"
    PARSE_FAILED            = "REF_500_PARSE_FAILED"
    IO_ERROR                = "REF_500_IO_ERROR"
    INTERNAL                = "REF_500_INTERNAL"

@dataclass
class RefactorChange:
    path: str
    action: str
    description: str
    diff: Optional[str] = None
    old_line: Optional[int] = None
    new_line: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BlastRadius:
    total_files: int = 0
    direct_dependents: int = 0
    transitive_dependents: int = 0
    test_files: int = 0
    core_modules: int = 0
    affected_symbols: int = 0
    confidence_score: int = 100

@dataclass
class ImpactResult:
    repository_id: str
    symbol_name: str
    source_file: str
    blast_radius: BlastRadius = field(default_factory=BlastRadius)
    affected_files: List[str] = field(default_factory=list)
    risk_level: str = "low"
    summary: str = ""
    recommendation: str = ""

@dataclass
class RefactorResult:
    status: str
    message: str
    repository_id: str
    action: str = ""
    changes: List[RefactorChange] = field(default_factory=list)
    blast_radius: Optional[BlastRadius] = None
    commit_hash: Optional[str] = None
    validation_result: Optional[str] = None
    error_code: Optional[str] = None
