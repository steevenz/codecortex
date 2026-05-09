"""
/**
 * @project   CodeCortex
 * @package   Core/Utils
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Utility for generating unified diffs.
 */
"""
import difflib

def generate_unified_diff(old_content: str, new_content: str, file_path: str) -> str:
    """Generate a git-style unified diff between two versions of a file."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )
    return "".join(diff)
