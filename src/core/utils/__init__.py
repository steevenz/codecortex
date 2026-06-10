"""
Core utilities — path, language, VCS, symbol, OS, serialisation, validation.

:project: CodeCortex
:package: Core.Utils
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from .path import norm_path, normalize_relpath, resolve_glob, canonicalize
from .language import (
    detect_language,
    is_source_code,
    classify_file,
    is_extension_in,
    EXTENSION_TO_LANGUAGE,
    SOURCE_CODE_EXTENSIONS,
    CONFIG_EXTENSIONS,
    DOC_EXTENSIONS,
    BINARY_EXTENSIONS,
)
from .vcs import (
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
)
from .symbol import parse_target, build_code_ref
from .system import get_owner, get_group, get_username
from .serialization import to_dict
from .validators import (
    validate_path,
    validate_file_path,
    validate_uuid,
    validate_max_depth,
    validate_positive_int,
    validate_range,
)
from .process import try_get_version
from .diff import generate_unified_diff
from .debug_log import info_logger, error_logger, warning_logger
from .version import Version, InvalidVersionError
from .headers import FileHeader, banner, FILE_HEADER_FORMATS

__all__ = [
    "norm_path",
    "normalize_relpath",
    "resolve_glob",
    "canonicalize",
    "detect_language",
    "is_source_code",
    "classify_file",
    "is_extension_in",
    "EXTENSION_TO_LANGUAGE",
    "SOURCE_CODE_EXTENSIONS",
    "CONFIG_EXTENSIONS",
    "DOC_EXTENSIONS",
    "BINARY_EXTENSIONS",
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
    "parse_target",
    "build_code_ref",
    "get_owner",
    "get_group",
    "get_username",
    "to_dict",
    "validate_path",
    "validate_file_path",
    "validate_uuid",
    "validate_max_depth",
    "validate_positive_int",
    "validate_range",
    "try_get_version",
    "generate_unified_diff",
    "info_logger",
    "error_logger",
    "warning_logger",
    "Version",
    "InvalidVersionError",
    "FileHeader",
    "banner",
    "FILE_HEADER_FORMATS",
]
