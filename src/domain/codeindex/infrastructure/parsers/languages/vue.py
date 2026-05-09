"""
/**
 * @project   CodeCortex
 * @package   CodeIndex/Parsers/Languages
 * @standard  Aegis-CrossStack-v1.0
 * * Vue SFC (Single File Component) parser.
 *   Extracts <script>, <template>, <style> sections from .vue files.
 *   Parses the script section using TypeScript/JavaScript TreeSitter grammar.
 *   Ported from GitNexus's vue-sfc-extractor.ts.
 */
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from src.core.tree_sitter_manager import execute_query, get_language_safe, create_parser

logger = logging.getLogger("CodeCortex.CodeIndex.Parsers.Vue")

SCRIPT_RE = re.compile(r'<script(\s[^>]*)?>([\s\S]*?)<\/script>', re.IGNORECASE)
TEMPLATE_RE = re.compile(r'<template(\s[^>]*)?>([\s\S]*)<\/template>', re.IGNORECASE)
STYLE_RE = re.compile(r'<style(\s[^>]*)?>([\s\S]*)<\/style>', re.IGNORECASE)
TEMPLATE_COMPONENT_RE = re.compile(r'<([A-Z][A-Za-z0-9]+)')


def extract_vue_sections(content: str) -> Dict[str, Any]:
    """Extract script, template, and style sections from .vue file."""
    result = {
        "script": None,
        "script_setup": False,
        "script_lang": "javascript",
        "template": None,
        "styles": [],
        "components": [],
    }
    
    # Extract script section
    for m in SCRIPT_RE.finditer(content):
        attrs = (m.group(1) or "").strip()
        script_content = m.group(2).strip()
        is_setup = "setup" in attrs
        lang_match = re.search(r'lang\s*=\s*["\']([^"\']+)["\']', attrs)
        lang = lang_match.group(1) if lang_match else "javascript"
        result["script"] = script_content or ""
        result["script_setup"] = is_setup
        result["script_lang"] = lang
    
    # Extract template section
    tmpl = TEMPLATE_RE.search(content)
    if tmpl:
        template_content = tmpl.group(2).strip()
        result["template"] = template_content
        # Find component usage in template
        for c in TEMPLATE_COMPONENT_RE.finditer(template_content):
            comp = c.group(1)
            if comp not in result["components"]:
                result["components"].append(comp)
    
    # Extract style sections
    for m in STYLE_RE.finditer(content):
        style_content = m.group(2).strip()
        if style_content:
            result["styles"].append(style_content)
    
    return result


def parse_vue(file_path: Path, **kwargs) -> Dict[str, Any]:
    """
    Parse a .vue file.
    Extracts script, template, and style sections.
    Parses the script using TypeScript/JavaScript TreeSitter.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"error": "cannot_read_file"}
    
    sections = extract_vue_sections(content)
    result = {
        "components": sections["components"],
        "template_components": sections["components"],
        "style_count": len(sections["styles"]),
        "setup_script": sections["script_setup"],
    }
    
    # Parse the script section
    script = sections.get("script", "")
    if script:
        lang = sections.get("script_lang", "javascript")
        ts_lang = "typescript" if lang in ("ts", "typescript") else "javascript"
        try:
            parser = create_parser(ts_lang)
            tree = parser.parse(script.encode("utf-8"))
            root = tree.root_node
            symbols = []
            
            # Extract functions
            for node, name in _find_nodes(root, "(function_declaration name: (identifier) @name)"):
                symbols.append({"name": name, "type": "function", "start_line": node.start_point[0] + 1, "end_line": node.end_point[0] + 1})
            for node, name in _find_nodes(root, "(arrow_function name: (identifier) @name)"):
                symbols.append({"name": name, "type": "function", "start_line": node.start_point[0] + 1, "end_line": node.end_point[0] + 1})
            
            # Extract classes
            for node, name in _find_nodes(root, "(class_declaration name: (identifier) @name)"):
                symbols.append({"name": name, "type": "class", "start_line": node.start_point[0] + 1, "end_line": node.end_point[0] + 1})
            
            # Extract exports
            for node, name in _find_nodes(root, "(export_statement name: (identifier) @name)"):
                for s in symbols:
                    if s["name"] == name:
                        s["is_exported"] = True
            
            result["symbols"] = symbols
        except Exception as e:
            logger.warning(f"Failed to parse Vue script: {e}")
            result["symbols"] = []
    else:
        result["symbols"] = []
    
    return result


def _find_nodes(root, query_str: str) -> List[Tuple[Any, str]]:
    """Execute TreeSitter query and yield (node, name) tuples."""
    try:
        from tree_sitter import Language, Query, QueryCursor
        lang = get_language_safe("javascript")
        if lang is None:
            return []
        query = Query(lang, query_str)
        cursor = QueryCursor(query)
        matches = cursor.matches(root)
        results = []
        for _pattern, captures in matches:
            for name, nodes in captures.items():
                for n in nodes:
                    results.append((n, n.text.decode("utf-8")))
        return results
    except Exception:
        return []
