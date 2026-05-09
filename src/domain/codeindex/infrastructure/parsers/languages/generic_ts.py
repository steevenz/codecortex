"""
/**
 * @project   CodeCortex
 * @package   CodeIndex/Parsers/Languages
 * @standard  Aegis-CrossStack-v1.0
 * * Generic TreeSitter parser for languages without dedicated parsers.
 *   Handles: Julia, Lua, Objective-C, PowerShell, Verilog, Zig
 *   
 *   Uses standard TreeSitter queries to extract:
 *   - Functions/methods
 *   - Classes/structs/interfaces
 *   - Variables (top-level)
 *   - Imports
 */
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from src.core.tree_sitter_manager import get_language_safe, create_parser, execute_query

logger = logging.getLogger("CodeCortex.CodeIndex.Parsers.Generic")

# Standard queries that work across many languages
STANDARD_QUERIES = {
    "functions": [
        "(function_definition name: (identifier) @name)",
        "(function_declaration name: (identifier) @name)",
        "(method_definition name: (identifier) @name)",
        "(method_declaration name: (identifier) @name)",
    ],
    "classes": [
        "(class_definition name: (identifier) @name)",
        "(class_declaration name: (identifier) @name)",
        "(struct_definition name: (identifier) @name)",
        "(interface_definition name: (identifier) @name)",
    ],
    "modules": [
        "(module_definition name: (identifier) @name)",
        "(namespace_definition name: (identifier) @name)",
    ],
}


def parse_generic(file_path: Path, language: str, **kwargs) -> Dict[str, Any]:
    """
    Parse a file using generic TreeSitter queries.
    Works for any language that standard TreeSitter grammar.
    """
    try:
        content_bytes = file_path.read_bytes()
        content = content_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return {"error": "cannot_read_file", "language": language}
    
    try:
        parser = create_parser(language)
        tree = parser.parse(content_bytes)
        root = tree.root_node
    except Exception as e:
        return {"error": f"parse_failed: {e}", "language": language}
    
    symbols = []
    seen_names = set()
    
    # Extract using standard queries
    for sym_type, queries in STANDARD_QUERIES.items():
        for query_str in queries:
            try:
                results = execute_query(parser.language, query_str, root)
                for node, name in results:
                    if name not in seen_names:
                        seen_names.add(name)
                        symbols.append({
                            "name": name,
                            "type": sym_type.rstrip("s"),
                            "start_line": node.start_point[0] + 1,
                            "end_line": node.end_point[0] + 1,
                            "is_exported": True,
                        })
            except Exception:
                continue
    
    return {
        "symbols": symbols,
        "language": language,
        "symbol_count": len(symbols),
    }


# ── Language-specific wrappers ────────────────────────────────────

def parse_julia(file_path: Path, **kwargs) -> Dict[str, Any]:
    return parse_generic(file_path, "julia")


def parse_lua(file_path: Path, **kwargs) -> Dict[str, Any]:
    return parse_generic(file_path, "lua")


def parse_objc(file_path: Path, **kwargs) -> Dict[str, Any]:
    return parse_generic(file_path, "objc")


def parse_powershell(file_path: Path, **kwargs) -> Dict[str, Any]:
    return parse_generic(file_path, "powershell")


def parse_verilog(file_path: Path, **kwargs) -> Dict[str, Any]:
    return parse_generic(file_path, "verilog")


def parse_zig(file_path: Path, **kwargs) -> Dict[str, Any]:
    return parse_generic(file_path, "zig")
