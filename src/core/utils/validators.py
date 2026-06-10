"""
Validation functions — path, UUID, and parameter validators.

:project: CodeCortex
:package: Core.Utils.Validators
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

def validate_path(path: str) -> Tuple[bool, str]:
    """Validate that a path is safe and exists.

    Returns:
        (is_valid, error_message). Error message is empty string when valid.
    """
    if not path or not isinstance(path, str):
        return False, "Path must be a non-empty string"
    if ".." in path:
        return False, "Path traversal detected"
    try:
        resolved_path = Path(path).resolve()
        if not resolved_path.exists():
            return False, f"Path does not exist: {path}"
        if not resolved_path.is_dir():
            return False, f"Path is not a directory: {path}"
        return True, ""
    except (OSError, ValueError, RuntimeError) as e:
        return False, f"Invalid path: {e}"

def validate_file_path(path: str) -> Tuple[bool, str]:
    """Validate that a file path is safe and the file exists.

    Returns:
        (is_valid, error_message).
    """
    if not path or not isinstance(path, str):
        return False, "Path must be a non-empty string"
    if ".." in path:
        return False, "Path traversal detected"
    try:
        resolved = Path(path).resolve()
        if not resolved.exists():
            return False, f"File does not exist: {path}"
        if not resolved.is_file():
            return False, f"Path is not a file: {path}"
        return True, ""
    except (OSError, ValueError, RuntimeError) as e:
        return False, f"Invalid path: {e}"

def validate_uuid(uuid_str: str) -> Tuple[bool, str]:
    """Validate that a string is a valid UUID.

    Returns:
        (is_valid, error_message).
    """
    if not uuid_str or not isinstance(uuid_str, str):
        return False, "UUID must be a non-empty string"
    try:
        from uuid import UUID
        UUID(uuid_str)
        return True, ""
    except (ValueError, AttributeError):
        return False, f"Invalid UUID format: {uuid_str}"

def validate_max_depth(depth: int) -> Tuple[bool, str]:
    """Validate that a max_depth parameter is within the allowed range [1, 20].

    Returns:
        (is_valid, error_message).
    """
    if not isinstance(depth, int):
        return False, "max_depth must be an integer"
    if depth < 1 or depth > 20:
        return False, "max_depth must be between 1 and 20"
    return True, ""

def validate_positive_int(value: int, name: str = "value") -> Tuple[bool, str]:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int):
        return False, f"{name} must be an integer"
    if value < 1:
        return False, f"{name} must be positive"
    return True, ""

def validate_range(value: int, min_val: int, max_val: int, name: str = "value") -> Tuple[bool, str]:
    """Validate that an integer is within [min_val, max_val]."""
    if not isinstance(value, int):
        return False, f"{name} must be an integer"
    if value < min_val or value > max_val:
        return False, f"{name} must be between {min_val} and {max_val}"
    return True, ""
