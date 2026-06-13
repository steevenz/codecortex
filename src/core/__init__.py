"""
Core package — Modular monolith infrastructure for CodeCortex.

:project: CodeCortex
:package: Core
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

from .config import (
    env_flag,
    load_version,
    new_request_id,
    utc_now_iso,
    utc_ts_to_iso,
    VersionProvider,
    get_db_path,
    get_data_dir,
    get_project_root,
)
from .config.ignore_patterns import (
    BUILTIN_IGNORE_PATTERNS,
    load_ignore_patterns,
    is_ignored,
)
from .database import (
    DatabaseManager,
    _LockedConnection,
    takeout_project,
    import_project,
    compact_database,
    cleanup_project,
)
from .graph import (
    GraphManager,
    GraphBackend,
    GraphResult,
    GraphSession,
    BACKEND_REGISTRY,
)
from .parser import TreeSitterManager, AstCache
from .templating import Engine, TemplateNotFoundError, TemplateRenderError
from .logging import get_logger, setup_logging, StructuredFormatter, log_event, Logger
from .telemetry import get_tracer_provider, record_metric, start_span
from .token import estimate_tokens, get_token_budget, optimize_response, TokenOptimization
from .errors import (
    ApiError,
    DomainError,
    ValidationError,
    api_response,
    extract_pagination,
)
from .security import (
    validate_url,
    ssrf_guarded_socket,
    safe_fetch,
    safe_fetch_text,
    validate_graph_path,
    sanitize_label,
    escape_html_label,
)
from .dtos import VcsInfo, MetricsInfo, GraphStatsInfo, FileStats
from .utils import (
    norm_path,
    normalize_relpath,
    resolve_glob,
    canonicalize,
    detect_language,
    is_source_code,
    classify_file,
    is_extension_in,
    EXTENSION_TO_LANGUAGE,
    SOURCE_CODE_EXTENSIONS,
    CONFIG_EXTENSIONS,
    DOC_EXTENSIONS,
    BINARY_EXTENSIONS,
    detect_vcs_type,
    is_git_repo,
    has_git_dir,
    get_canonical_repo_root,
    get_current_commit,
    get_remote_url,
    normalize_remote_url,
    parse_repo_name_from_url,
    get_inferred_repo_name,
    extract_vcs_metadata,
    extract_git_metadata,
    extract_svn_metadata,
    get_changed_files,
    ensure_codecortex_ignored,
    parse_target,
    build_code_ref,
    get_owner,
    get_group,
    get_username,
    to_dict,
    validate_path,
    validate_file_path,
    validate_uuid,
    validate_max_depth,
    validate_positive_int,
    validate_range,
    try_get_version,
    generate_unified_diff,
    Version,
    InvalidVersionError,
    FileHeader,
    banner,
    FILE_HEADER_FORMATS,
)

__all__ = [
    # Config
    "env_flag",
    "load_version",
    "new_request_id",
    "utc_now_iso",
    "utc_ts_to_iso",
    "VersionProvider",
    "get_db_path",
    "get_data_dir",
    "get_project_root",
    "BUILTIN_IGNORE_PATTERNS",
    "load_ignore_patterns",
    "is_ignored",
    # Database
    "DatabaseManager",
    "_LockedConnection",
    "takeout_project",
    "import_project",
    "compact_database",
    "cleanup_project",
    # Graph
    "GraphManager",
    "GraphBackend",
    "GraphResult",
    "GraphSession",
    "BACKEND_REGISTRY",
    # Parser
    "TreeSitterManager",
    "AstCache",
    # Templating
    "Engine",
    "TemplateNotFoundError",
    "TemplateRenderError",
    # Logging
    "get_logger",
    "setup_logging",
    "StructuredFormatter",
    "Logger",
    "log_event",
    # Telemetry
    "get_tracer_provider",
    "record_metric",
    "start_span",
    # Token
    "estimate_tokens",
    "get_token_budget",
    "optimize_response",
    "TokenOptimization",
    # Errors
    "ApiError",
    "DomainError",
    "ValidationError",
    "api_response",
    "extract_pagination",
    # Security
    "validate_url",
    "ssrf_guarded_socket",
    "safe_fetch",
    "safe_fetch_text",
    "validate_graph_path",
    "sanitize_label",
    "escape_html_label",
    # DTOs
    "VcsInfo",
    "MetricsInfo",
    "GraphStatsInfo",
    "FileStats",
    # Utils — Path
    "norm_path",
    "normalize_relpath",
    "resolve_glob",
    "canonicalize",
    # Utils — Language
    "detect_language",
    "is_source_code",
    "classify_file",
    "is_extension_in",
    "EXTENSION_TO_LANGUAGE",
    "SOURCE_CODE_EXTENSIONS",
    "CONFIG_EXTENSIONS",
    "DOC_EXTENSIONS",
    "BINARY_EXTENSIONS",
    # Utils — VCS
    "detect_vcs_type",
    "is_git_repo",
    "has_git_dir",
    "get_canonical_repo_root",
    "get_current_commit",
    "get_remote_url",
    "normalize_remote_url",
    "parse_repo_name_from_url",
    "get_inferred_repo_name",
    "extract_vcs_metadata",
    "extract_git_metadata",
    "extract_svn_metadata",
    "get_changed_files",
    "ensure_codecortex_ignored",
    # Utils — Symbol
    "parse_target",
    "build_code_ref",
    # Utils — OS
    "get_owner",
    "get_group",
    "get_username",
    # Utils — Serialisation
    "to_dict",
    # Utils — Validation
    "validate_path",
    "validate_file_path",
    "validate_uuid",
    "validate_max_depth",
    "validate_positive_int",
    "validate_range",
    "try_get_version",
    "generate_unified_diff",
    "Version",
    "InvalidVersionError",
    "FileHeader",
    "banner",
    "FILE_HEADER_FORMATS",
]
