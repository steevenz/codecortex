"""
Unified diff generation — wraps ``difflib.unified_diff``.

:project: CodeCortex
:package: Core.Utils.Diff
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

import difflib
from typing import List, Optional

def generate_unified_diff(
    original,
    modified,
    fromfile: str = '',
    tofile: str = '',
    lineterm: str = '\n'
) -> str:
    """Generate a unified diff string.

    Accepts either a list of lines or a raw string for *original* and *modified*.
    """
    if isinstance(original, str):
        original = original.splitlines(keepends=True)
    if isinstance(modified, str):
        modified = modified.splitlines(keepends=True)
    return '\n'.join(difflib.unified_diff(
        original, modified, fromfile=fromfile, tofile=tofile, lineterm=lineterm
    ))
