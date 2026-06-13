"""
Call and inheritance resolution logic ported from legacy codegraph.

:project: CodeCortex
:package: Modules.Codegraph.Services.Resolution
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

from .calls import resolve_function_call, build_function_call_groups
from .inheritance import resolve_inheritance_link, build_inheritance_and_csharp_files

__all__ = [
    "resolve_function_call",
    "build_function_call_groups",
    "resolve_inheritance_link",
    "build_inheritance_and_csharp_files",
]
