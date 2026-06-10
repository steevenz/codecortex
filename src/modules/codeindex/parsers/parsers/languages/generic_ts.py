"""
Generic TreeSitter parser for languages without dedicated parsers.
Handles: Julia, Lua, Objective-C, PowerShell, Verilog, Zig.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Generic_ts
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from src.core.parser.tree_sitter_manager import get_language_safe, create_parser, execute_query

logger = logging.getLogger("CodeCortex.CodeIndex.Parsers.Generic")

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
    "calls": [
        "(call_expression function: (identifier) @name)",
        "(call_expression function: (field_expression field: (field_identifier) @name))",
        "(invocation_expression function: (identifier) @name)",
    ],
    "imports": [
        "(import_declaration) @import",
        "(use_declaration) @use",
    ],
    "variables": [
        "(variable_declaration declarator: (init_declarator declarator: (identifier) @name))",
        "(local_variable_declaration declarator: (variable_declarator name: (identifier) @name))",
    ],
}

def _get_node_text(node) -> str:
    try:
        return node.text.decode("utf-8")
    except Exception:
        return ""

def _get_class_context(node, language_obj) -> Optional[str]:
    """Walk parent chain to find containing class-like construct."""
    current = node.parent
    while current:
        ctype = current.type
        if ctype in ("class_definition", "class_declaration", "struct_definition",
                      "interface_definition", "module_definition", "namespace_definition"):
            name_node = current.child_by_field_name("name")
            if name_node:
                return _get_node_text(name_node)
        current = current.parent
    return None

def _try_extract_params(node, language_obj) -> List[str]:
    """Try to extract parameter names from a function node."""
    for field in ("parameters", "formal_parameters", "parameter_list", "params"):
        pn = node.child_by_field_name(field)
        if pn:
            out = []
            for child in pn.named_children:
                name_node = child.child_by_field_name("name")
                if name_node:
                    out.append(_get_node_text(name_node))
                elif child.type == "identifier":
                    out.append(_get_node_text(child))
            return out
    return []

def _try_extract_bases(node) -> List[str]:
    """Try to extract base classes from a class-like node."""
    for field in ("bases", "superclasses", "supertype", "inheritance"):
        bn = node.child_by_field_name(field)
        if bn:
            return [_get_node_text(c) for c in bn.named_children
                    if c.type not in (",", "(", ")")]
    return []

def parse_generic(file_path: Path, language: str, **kwargs) -> Dict[str, Any]:
    try:
        content_bytes = file_path.read_bytes()
        content_bytes = content_bytes
    except Exception:
        return {"path": str(file_path), "error": "cannot_read_file", "lang": language}

    try:
        parser = create_parser(language)
        tree = parser.parse(content_bytes)
        root = tree.root_node
    except Exception as e:
        return {"path": str(file_path), "error": str(e), "lang": language}

    functions = []
    classes = []
    variables = []
    imports = []
    function_calls = []

    seen_func_names = set()
    for q in STANDARD_QUERIES.get("functions", []):
        try:
            for node, name in execute_query(parser.language, q, root):
                if name not in seen_func_names:
                    seen_func_names.add(name)
                    class_ctx = _get_class_context(node, parser.language)
                    functions.append({
                        "name": name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "args": _try_extract_params(node, parser.language),
                        "class_context": class_ctx,
                        "function_calls": [],
                        "lang": language,
                        "is_dependency": False,
                    })
        except Exception:
            continue

    seen_class_names = set()
    for q in STANDARD_QUERIES.get("classes", []):
        try:
            for node, name in execute_query(parser.language, q, root):
                if name not in seen_class_names:
                    seen_class_names.add(name)
                    classes.append({
                        "name": name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "bases": _try_extract_bases(node),
                        "lang": language,
                        "is_dependency": False,
                    })
        except Exception:
            continue

    for q in STANDARD_QUERIES.get("modules", []):
        try:
            for node, name in execute_query(parser.language, q, root):
                if name not in seen_class_names:
                    seen_class_names.add(name)
                    classes.append({
                        "name": name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "bases": [],
                        "lang": language,
                        "is_dependency": False,
                    })
        except Exception:
            continue

    seen_var_names = set()
    for q in STANDARD_QUERIES.get("variables", []):
        try:
            for node, name in execute_query(parser.language, q, root):
                if name not in seen_var_names:
                    seen_var_names.add(name)
                    variables.append({
                        "name": name,
                        "line_number": node.start_point[0] + 1,
                        "lang": language,
                    })
        except Exception:
            continue

    seen_call_names = set()
    for q in STANDARD_QUERIES.get("calls", []):
        try:
            for node, name in execute_query(parser.language, q, root):
                if name not in seen_call_names:
                    seen_call_names.add(name)
                    function_calls.append({
                        "name": name,
                        "line_number": node.start_point[0] + 1,
                        "lang": language,
                    })
        except Exception:
            continue

    for q in STANDARD_QUERIES.get("imports", []):
        try:
            for node, _tag in execute_query(parser.language, q, root):
                text = _get_node_text(node)[:120]
                imports.append({
                    "name": text,
                    "source": text,
                    "line_number": node.start_point[0] + 1,
                    "lang": language,
                })
        except Exception:
            continue

    return {
        "path": str(file_path),
        "functions": functions,
        "classes": classes,
        "variables": variables,
        "imports": imports,
        "function_calls": function_calls,
        "is_dependency": False,
        "lang": language,
        "language": language,
        "symbol_count": len(functions) + len(classes),
        "symbols": [{"name": f["name"], "type": "function",
                      "start_line": f["line_number"], "end_line": f["end_line"],
                      "is_exported": True} for f in functions]
                  + [{"name": c["name"], "type": "class",
                      "start_line": c["line_number"], "end_line": c["end_line"],
                      "is_exported": True} for c in classes],
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
