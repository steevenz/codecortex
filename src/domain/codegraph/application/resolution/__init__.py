"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeGraph/Resolution
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Call and inheritance resolution logic ported from legacy codegraph.
 */
"""

from .calls import resolve_function_call, build_function_call_groups
from .inheritance import resolve_inheritance_link, build_inheritance_and_csharp_files

__all__ = [
    "resolve_function_call",
    "build_function_call_groups",
    "resolve_inheritance_link",
    "build_inheritance_and_csharp_files",
]
