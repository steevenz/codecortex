"""
Vue SFC parser — tree-sitter-vue grammar (primary) with regex+JS/TS fallback.
Output standard format: functions[], classes[], variables[], imports[], calls[].

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Vue
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("CodeCortex.CodeIndex.Parsers.Vue")

SCRIPT_RE = re.compile(r'<script(\s[^>]*)?>([\s\S]*?)<\/script>', re.IGNORECASE)
TEMPLATE_RE = re.compile(r'<template(\s[^>]*)?>([\s\S]*)<\/template>', re.IGNORECASE)
STYLE_RE = re.compile(r'<style(\s[^>]*)?>([\s\S]*)<\/style>', re.IGNORECASE)
TEMPLATE_COMPONENT_RE = re.compile(r'<([A-Z][A-Za-z0-9]+)')

def _text(node) -> str:
    try:
        return node.text.decode("utf-8")
    except Exception:
        return ""

def _try_extract_args(params_node) -> List[str]:
    args = []
    if not params_node:
        return args
    for p in params_node.named_children:
        if p.type == "identifier":
            args.append(_text(p))
        elif p.child_by_field_name("name"):
            args.append(_text(p.child_by_field_name("name")))
        elif p.child_by_field_name("pattern"):
            args.append(_text(p.child_by_field_name("pattern")))
    return args

def _extract_class_ctx(fn_node, class_names: set) -> Optional[str]:
    cur = fn_node.parent
    while cur:
        if cur.type in ("class_declaration",):
            n = cur.child_by_field_name("name")
            return _text(n) if n else None
        cur = cur.parent
    return None

def _parse_script_with_ts(script: str, lang: str) -> Dict[str, Any]:
    """Parse script content using JS/TS tree-sitter."""
    try:
        from src.core.parser.tree_sitter_manager import get_language_safe, create_parser, execute_query
        ts_lang = "typescript" if lang in ("ts", "typescript") else "javascript"
        language_obj = get_language_safe(ts_lang)
        parser = create_parser(ts_lang)
        tree = parser.parse(script.encode("utf-8"))
        root = tree.root_node
    except Exception:
        return {}

    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    variables: List[Dict[str, Any]] = []
    imports: List[Dict[str, Any]] = []
    calls: List[Dict[str, Any]] = []

    seen_funcs: set = set()
    for q in [
        "(function_declaration name: (identifier) @n params: (formal_parameters) @p) @fn",
        "(method_definition name: (property_identifier) @n params: (formal_parameters) @p) @fn",
        "(variable_declarator name: (identifier) @n value: (arrow_function params: (formal_parameters) @p)) @fn",
        "(variable_declarator name: (identifier) @n value: (function params: (formal_parameters) @p)) @fn",
    ]:
        try:
            for node, tag in execute_query(language_obj, q, root):
                if tag == "n":
                    nm = _text(node)
                    if nm not in seen_funcs:
                        seen_funcs.add(nm)
                        fn_node = node.parent
                        while fn_node and fn_node.type not in ("function_declaration", "method_definition", "variable_declarator", "arrow_function", "function"):
                            fn_node = fn_node.parent
                        args = []
                        # find params
                        for _, pt in execute_query(language_obj, q, root):
                            if pt == "p":
                                pn = node.parent.child_by_field_name("parameters") or node.parent.child_by_field_name("formal_parameters") or node.parent.child_by_field_name("params")
                                if pn:
                                    args = _try_extract_args(pn)
                                break
                        existing_class_names = {c.get("name", "") for c in classes}
                        functions.append({
                            "name": nm,
                            "line_number": node.start_point[0] + 1 + script[:node.start_byte].count('\n'),
                            "end_line": (fn_node.end_point[0] + 1 + script[:fn_node.start_byte].count('\n')) if fn_node else node.start_point[0] + 1,
                            "args": args,
                            "class_context": _extract_class_ctx(node, existing_class_names),
                            "function_calls": [],
                            "lang": ts_lang,
                            "is_dependency": False,
                        })
        except Exception:
            continue

    try:
        q = "(class_declaration) @c"
        for node, tag in execute_query(language_obj, q, root):
            if tag == "c":
                n = node.child_by_field_name("name")
                if n:
                    nm = _text(n)
                    sup = node.child_by_field_name("superclass")
                    bases = [_text(sup)] if sup else []
                    classes.append({
                        "name": nm, "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "bases": bases, "lang": ts_lang, "is_dependency": False,
                    })
    except Exception:
        pass

    try:
        q = "(variable_declarator name: (identifier) @n)"
        seen_vars: set = set()
        for node, tag in execute_query(language_obj, q, root):
            if tag == "n":
                nm = _text(node)
                if nm not in seen_vars and nm not in seen_funcs:
                    seen_vars.add(nm)
                    variables.append({"name": nm, "line_number": node.start_point[0] + 1, "lang": ts_lang})
    except Exception:
        pass

    try:
        q = "(import_statement) @i"
        for node, tag in execute_query(language_obj, q, root):
            if tag == "i":
                src = node.child_by_field_name("source")
                s = _text(src).strip("'\"") if src else ""
                imports.append({"name": s, "source": s, "line_number": node.start_point[0] + 1, "lang": ts_lang})
    except Exception:
        pass

    for q in [
        "(call_expression function: (identifier) @n)",
        "(call_expression function: (member_expression property: (property_identifier) @n))",
    ]:
        try:
            seen_c: set = set()
            for node, tag in execute_query(language_obj, q, root):
                if tag == "n":
                    nm = _text(node)
                    if nm not in seen_c:
                        seen_c.add(nm)
                        calls.append({"name": nm, "line_number": node.start_point[0] + 1, "lang": ts_lang})
        except Exception:
            continue

    return {"functions": functions, "classes": classes, "variables": variables,
            "imports": imports, "function_calls": calls, "lang": ts_lang}

def extract_vue_sections(content: str) -> Dict[str, Any]:
    """Backward compat: public alias."""
    return _extract_vue_sections(content)

def _extract_vue_sections(content: str) -> Dict[str, Any]:
    result = {
        "script": None, "script_setup": False, "script_lang": "javascript",
        "template": None, "styles": [], "components": [],
    }
    for m in SCRIPT_RE.finditer(content):
        attrs = (m.group(1) or "").strip()
        result["script"] = (m.group(2) or "").strip()
        result["script_setup"] = "setup" in attrs
        lm = re.search(r'lang\s*=\s*["\']([^"\']+)["\']', attrs)
        result["script_lang"] = lm.group(1) if lm else "javascript"
    tmpl = TEMPLATE_RE.search(content)
    if tmpl:
        result["template"] = tmpl.group(2).strip()
        for c in TEMPLATE_COMPONENT_RE.finditer(tmpl.group(2)):
            comp = c.group(1)
            if comp not in result["components"]:
                result["components"].append(comp)
    for m in STYLE_RE.finditer(content):
        sc = m.group(2).strip()
        if sc:
            result["styles"].append(sc)
    return result

def _parse_vue_ts(content: str, path_str: str) -> Dict[str, Any]:
    """Try tree-sitter-vue grammar for full SFC parsing."""
    try:
        from src.core.parser.tree_sitter_manager import get_language_safe, create_parser, execute_query
        vue_lang = get_language_safe("vue")
        vue_parser = create_parser("vue")
        tree = vue_parser.parse(content.encode("utf-8"))
        root = tree.root_node
    except Exception:
        raise ImportError("tree-sitter-vue not available")

    result: Dict[str, Any] = {
        "lang": "vue", "is_dependency": False, "path": path_str,
        "functions": [], "classes": [], "variables": [], "imports": [], "function_calls": [],
        "framework": "vue", "components": [],
    }

    # Extract template components from element nodes
    def _walk_elements(node, depth=0):
        if depth > 10:
            return
        if node.type == "element":
            start_tag = node.child_by_field_name("start_tag") or node
            tag_name_node = start_tag.child_by_field_name("name") if start_tag else None
            if tag_name_node:
                name = _text(tag_name_node)
                if name and name[0].isupper() and name not in result["components"]:
                    result["components"].append(name)
        for child in node.named_children:
            _walk_elements(child, depth + 1)

    _walk_elements(root)

    # Find script section content
    script_text = None
    script_lang = "javascript"
    for child in root.named_children:
        if child.type == "script_element":
            raw = child.child_by_field_name("text") or child.child_by_field_name("raw_text")
            if raw:
                script_text = _text(raw)
            # Check lang attribute
            start_tag = child.child_by_field_name("start_tag")
            if start_tag:
                for attr in start_tag.named_children:
                    if attr.type == "attribute" and _text(attr.child_by_field_name("name")) == "lang":
                        val = attr.child_by_field_name("value")
                        if val:
                            script_lang = _text(val).strip("'\"")
        elif child.type == "style_element":
            pass  # CSS handled separately

    # Parse script with JS/TS tree-sitter
    if script_text:
        syms = _parse_script_with_ts(script_text, script_lang)
        result["functions"] = syms.get("functions", [])
        result["classes"] = syms.get("classes", [])
        result["variables"] = syms.get("variables", [])
        result["imports"] = syms.get("imports", [])
        result["function_calls"] = syms.get("function_calls", [])

    return result

def parse_vue(file_path: Path, **kwargs) -> Dict[str, Any]:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"error": "cannot_read_file", "lang": "vue"}

    path_str = str(file_path)

    # Primary: tree-sitter-vue grammar if available
    try:
        return _parse_vue_ts(content, path_str)
    except ImportError:
        pass

    # Fallback: regex + JS/TS tree-sitter
    sections = _extract_vue_sections(content)
    script = sections.get("script", "")
    script_lang = sections.get("script_lang", "javascript")

    result: Dict[str, Any] = {
        "lang": "vue", "is_dependency": False, "path": path_str,
        "functions": [], "classes": [], "variables": [], "imports": [], "function_calls": [],
        "framework": "vue", "components": sections.get("components", []),
    }

    if script:
        syms = _parse_script_with_ts(script, script_lang)
        result["functions"] = syms.get("functions", [])
        result["classes"] = syms.get("classes", [])
        result["variables"] = syms.get("variables", [])
        result["imports"] = syms.get("imports", [])
        result["function_calls"] = syms.get("function_calls", [])

    return result
