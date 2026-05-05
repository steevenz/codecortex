"""
/**
 * @project   CodeCortex
 * @package   Domain/Refactor/Core
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Data Transfer Objects for Refactor Domain.
 */
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class RefactorChange:
    path: str
    action: str  # 'modify', 'move', 'delete'
    description: str
    diff: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RefactorResult:
    status: str
    message: str
    repository_id: str
    changes: List[RefactorChange] = field(default_factory=list)
    commit_hash: Optional[str] = None
    error_code: Optional[str] = None

@dataclass
class ImpactAnalysisResult:
    repository_id: str
    symbol_name: str
    source_file: str
    affected_files: List[str] = field(default_factory=list)
    call_sites: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    risk_level: str = "low" # low, medium, high
    summary: str = ""
