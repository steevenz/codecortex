"""
Data Transfer Objects for CodeAnalysis Domain.
Supports analyze, search, audit, status tools.

:project: CodeCortex
:package: Modules.Codeanalysis.Core.Dtos
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# ═══════════════════════════════════════════════════════════════════
# CODE ANALYZE DTOs
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AnalyzedSymbol:
    name: str
    kind: str
    file_path: str
    line_start: int
    line_end: int
    signature: str = ""
    docstring: str = ""
    parent_symbol: Optional[str] = None
    calls: List[str] = field(default_factory=list)
    referenced_by: List[str] = field(default_factory=list)

@dataclass
class AnalyzedEdge:
    from_symbol: str
    to_symbol: str
    relation: str
    weight: float = 1.0

@dataclass
class AnalyzeRequest:
    target: str
    targets: Optional[List[str]] = None  # Batch: multiple targets
    mode: str = "auto"
    summary: Optional[bool] = None
    max_depth: int = 3
    focus: Optional[str] = None
    follow_depth: int = 1
    cursor: Optional[str] = None
    page_size: int = 100
    include_docstring: bool = True
    include_comments: bool = False
    repo_id: Optional[str] = None
    parallel: bool = True  # Enable parallel processing for batch
    max_workers: int = 4  # Thread pool size for parallel processing

@dataclass
class AnalyzeResult:
    mode: str
    target: str
    symbols: List[AnalyzedSymbol] = field(default_factory=list)
    edges: List[AnalyzedEdge] = field(default_factory=list)
    count: int = 0
    next_cursor: Optional[str] = None
    has_more: bool = False
    tree: Optional[List[Dict[str, Any]]] = None

# ═══════════════════════════════════════════════════════════════════
# CODE SEARCH DTOs
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SearchRequest:
    query: str
    search_type: str = "symbol"
    limit: int = 50
    cursor: Optional[int] = None
    repo_id: Optional[str] = None
    file_pattern: str = "*"
    include_content: bool = False

@dataclass
class SearchMatch:
    symbol: str
    kind: str
    file: str
    line: int
    signature: str = ""
    docstring: str = ""
    confidence: float = 1.0
    repo_id: Optional[str] = None

@dataclass
class SearchResult:
    items: List[SearchMatch] = field(default_factory=list)
    next_cursor: Optional[int] = None
    total: int = 0
    search_type: str = "symbol"

# ═══════════════════════════════════════════════════════════════════
# CODE AUDIT DTOs
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AuditFinding:
    category: str
    severity: str
    file: str
    line: int
    column: int = 0
    code: str = ""
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    context: str = ""
    confidence: float = 1.0
    remediation: str = ""
    standard_ref: str = ""
    # Auto-fix capabilities (10/10 AI coder impact feature)
    auto_fix_available: bool = False  # Whether an automated fix is possible
    auto_fix_code: Optional[str] = None  # The fix code/snippet
    auto_fix_description: str = ""  # Description of what the fix does
    fix_applied: bool = False  # Whether fix was applied
    fix_diff: Optional[str] = None  # Unified diff of the fix

@dataclass
class AuditRequest:
    target: str
    scan_categories: Optional[List[str]] = None
    severity_threshold: str = "medium"
    entropy_threshold: float = 4.5
    include_comments: bool = False
    max_file_size_kb: int = 1024
    files: Optional[List[str]] = None
    output_format: str = "json"
    use_ast: bool = True
    use_aiignore: bool = True
    repository_id: Optional[str] = None
    since: Optional[str] = None
    db_path: Optional[str] = None
    # Smart caching and performance options (10/10 AI coder impact)
    cache_ttl: int = 300  # Cache TTL in seconds
    force_refresh: bool = False  # Bypass cache
    enable_auto_fix: bool = False  # Generate auto-fix suggestions
    apply_auto_fix: bool = False  # Apply auto-fixes to files (DANGEROUS - use with dry_run)
    dry_run: bool = True  # When true, don't actually modify files even with apply_auto_fix

@dataclass
class AuditResult:
    target: str
    scan_categories: List[str]
    scanned_files: int = 0
    summary: Dict[str, int] = field(default_factory=dict)
    compliance_score: int = 100
    findings: List[AuditFinding] = field(default_factory=list)
    recommendations: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, str]] = field(default_factory=list)

# ═══════════════════════════════════════════════════════════════════
# CODE STATUS DTOs
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MetricsInfo:
    files: int = 0
    directories: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    comment_ratio: float = 0.0
    languages: Dict[str, int] = field(default_factory=dict)

@dataclass
class VcsInfo:
    type: str = "none"
    branch: Optional[str] = None
    commit: Optional[str] = None
    last_commit_date: Optional[str] = None
    uncommitted_changes: int = 0
    untracked_files: int = 0

@dataclass
class GraphStatsInfo:
    nodes: int = 0
    edges: int = 0
    density: float = 0.0
    components: int = 0

@dataclass
class StatusRequest:
    path: str
    repo_id: Optional[str] = None
    include_metrics: bool = True
    include_vcs: bool = True
    include_symbols: bool = True
    language: Optional[str] = None

@dataclass
class StatusResult:
    target: str
    repo_id: Optional[str] = None
    summary: Optional[MetricsInfo] = None
    symbols: Dict[str, int] = field(default_factory=dict)
    graph_stats: Optional[GraphStatsInfo] = None
    vcs: Optional[VcsInfo] = None
