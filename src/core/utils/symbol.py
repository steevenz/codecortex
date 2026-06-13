"""
Symbol utilities — target parsing and code reference builders.

:project: CodeCortex
:package: Core.Utils.Symbol
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

from typing import Optional, Tuple

def parse_target(target: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a target string into (source_file, symbol_name).

    Supported formats:
    - ``file.py::symbol``   (Python-style double-colon)
    - ``file.py:symbol``    (colon separator)
    - ``file.py:42``        (line number — returns line as string, symbol_name=None)

    Args:
        target: The target string to parse.

    Returns:
        (source_file, symbol_name). Both may be None for invalid input.
    """
    if not target or not isinstance(target, str):
        return None, None

    target = target.strip()

    # Double-colon: file::symbol
    if "::" in target:
        parts = target.split("::", 1)
        return parts[0].strip() or None, parts[1].strip() or None

    # Single colon: file:symbol or file:line
    if ":" in target:
        parts = target.split(":", 1)
        return parts[0].strip() or None, parts[1].strip() or None

    return target, None

def build_code_ref(
    file_path: str,
    symbol_type: str,
    qualified_name: str,
    start_line: int,
) -> str:
    """Build a unique code reference string.

    Format: ``{file_path}:{symbol_type}:{qualified_name}@{start_line}``

    Args:
        file_path: Relative file path.
        symbol_type: Symbol type (e.g. ``'class'``, ``'function'``).
        qualified_name: Fully qualified symbol name.
        start_line: Line number where the symbol starts.

    Returns:
        Unique code reference string.
    """
    return f"{file_path}:{symbol_type}:{qualified_name}@{start_line}"
