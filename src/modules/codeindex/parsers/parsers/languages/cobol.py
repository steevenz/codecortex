"""
COBOL parser — tree-sitter-cobol (primary) with regex fallback.
Output standard format: functions[], classes[], variables[], imports[], calls[].

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Cobol
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("CodeCortex.CodeIndex.Parsers.COBOL")

COBOL_EXTENSIONS = {'.cob', '.cbl', '.cobol', '.cpy', '.copybook', '.jcl', '.job', '.proc'}

RE_DIVISION = re.compile(r'(IDENTIFICATION|ID|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\.', re.IGNORECASE | re.MULTILINE)
RE_SECTION = re.compile(r'(\w[\w-]*)\s+SECTION\.', re.IGNORECASE | re.MULTILINE)
RE_PARAGRAPH = re.compile(r'(\w[\w-]*)\.\s*$', re.MULTILINE)
RE_DATA_ITEM = re.compile(r'(\d{2})\s+(\w[\w-]*)\s*(?:PIC\s+(\S+))?\s*(?:VALUE\s+(.+?))?\.', re.IGNORECASE | re.MULTILINE)
RE_COPY = re.compile(r'COPY\s+(\w[\w-]*(?:\/\w[\w-]*)*)\s*(?:REPLACING.*)?\.', re.IGNORECASE | re.MULTILINE)
RE_CALL = re.compile(r'CALL\s+[\'"](\w[\w-]*)', re.IGNORECASE | re.MULTILINE)
RE_PROGRAM_ID = re.compile(r'PROGRAM-ID\.\s*(\w[\w-]*)', re.IGNORECASE | re.MULTILINE)

def _text(node) -> str:
    try:
        return node.text.decode("utf-8")
    except Exception:
        return ""

def _parse_with_ts(content: str, path_str: str) -> Dict[str, Any]:
    """Try tree-sitter-cobol grammar."""
    try:
        from src.core.parser.tree_sitter_manager import get_language_safe, create_parser, execute_query
        lang = get_language_safe("cobol")
        parser = create_parser("cobol")
        tree = parser.parse(content.encode("utf-8"))
        root = tree.root_node
    except Exception:
        raise ImportError("tree-sitter-cobol not available")

    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    variables: List[Dict[str, Any]] = []
    imports: List[Dict[str, Any]] = []
    calls: List[Dict[str, Any]] = []

    # Extract program names as classes
    try:
        q = "(program_name) @p"
        for node, tag in execute_query(lang, q, root):
            if tag == "p":
                nm = _text(node)
                classes.append({
                    "name": nm, "line_number": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "bases": [], "lang": "cobol", "is_dependency": False,
                })
                functions.append({
                    "name": nm, "line_number": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1, "args": [],
                    "class_context": None, "function_calls": [],
                    "lang": "cobol", "is_dependency": False,
                })
    except Exception:
        pass

    # Extract paragraphs as functions
    try:
        q = "(paragraph_name) @p"
        seen: set = set()
        for node, tag in execute_query(lang, q, root):
            if tag == "p":
                nm = _text(node)
                if nm not in seen:
                    seen.add(nm)
                    functions.append({
                        "name": nm, "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1, "args": [],
                        "class_context": None, "function_calls": [],
                        "lang": "cobol", "is_dependency": False,
                    })
    except Exception:
        pass

    # Extract sections as functions
    try:
        q = "(section_name) @s"
        seen: set = set()
        for node, tag in execute_query(lang, q, root):
            if tag == "s":
                nm = _text(node)
                if nm not in seen:
                    seen.add(nm)
                    functions.append({
                        "name": f"{nm}_SECTION", "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1, "args": [],
                        "class_context": None, "function_calls": [],
                        "lang": "cobol", "is_dependency": False,
                    })
    except Exception:
        pass

    # Extract data items as variables
    try:
        q = "(data_name) @d"
        seen: set = set()
        for node, tag in execute_query(lang, q, root):
            if tag == "d":
                nm = _text(node)
                if nm not in seen:
                    seen.add(nm)
                    variables.append({"name": nm, "line_number": node.start_point[0] + 1, "lang": "cobol"})
    except Exception:
        pass

    # Extract CALL statements
    try:
        q = "(call_statement name: (identifier) @c)"
        seen: set = set()
        for node, tag in execute_query(lang, q, root):
            if tag == "c":
                nm = _text(node)
                if nm not in seen:
                    seen.add(nm)
                    calls.append({"name": nm, "line_number": node.start_point[0] + 1, "lang": "cobol"})
    except Exception:
        pass

    # Extract COPY statements as imports
    try:
        q = "(copy_statement name: (identifier) @c)"
        for node, tag in execute_query(lang, q, root):
            if tag == "c":
                nm = _text(node)
                imports.append({"name": nm, "source": nm, "line_number": node.start_point[0] + 1, "lang": "cobol"})
    except Exception:
        pass

    return {
        "path": path_str, "lang": "cobol", "is_dependency": False,
        "functions": functions, "classes": classes, "variables": variables,
        "imports": imports, "function_calls": calls,
        "language": "cobol", "extensions": list(COBOL_EXTENSIONS),
    }

def is_cobol_file(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in COBOL_EXTENSIONS

def _preprocess_cobol(source: str) -> str:
    lines = source.split('\n')
    cleaned = []
    for line in lines:
        if len(line) > 6 and line[6] in ('*', '/'):
            continue
        if len(line) > 72:
            line = line[:72]
        cleaned.append(line.rstrip())
    return '\n'.join(cleaned)

def _parse_with_regex(content: str, path_str: str) -> Dict[str, Any]:
    """Regex-based COBOL parsing fallback."""
    source = _preprocess_cobol(content)
    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    variables: List[Dict[str, Any]] = []
    imports: List[Dict[str, Any]] = []
    calls: List[Dict[str, Any]] = []

    # PROGRAM-ID as class
    m = RE_PROGRAM_ID.search(source)
    if m:
        prog_id = m.group(1)
        prog_line = source[:m.start()].count('\n') + 1
        classes.append({
            "name": prog_id, "line_number": prog_line, "end_line": prog_line + 10,
            "bases": [], "lang": "cobol", "is_dependency": False,
        })

    # DIVISIONs as functions
    for m in RE_DIVISION.finditer(source):
        div_name = m.group(1).upper()
        if div_name in ('IDENTIFICATION', 'ID'):
            continue
        div_line = source[:m.start()].count('\n') + 1
        functions.append({
            "name": f"{div_name}_DIVISION", "line_number": div_line, "end_line": div_line + 1,
            "args": [], "class_context": None, "function_calls": [],
            "lang": "cobol", "is_dependency": False,
        })

    # SECTIONs as functions
    for m in RE_SECTION.finditer(source):
        sec_name = m.group(1)
        sec_line = source[:m.start()].count('\n') + 1
        functions.append({
            "name": sec_name, "line_number": sec_line, "end_line": sec_line + 1,
            "args": [], "class_context": None, "function_calls": [],
            "lang": "cobol", "is_dependency": False,
        })

    # PARAGRAPHs as functions
    proc_start = source.upper().find('PROCEDURE DIVISION')
    if proc_start >= 0:
        proc_source = source[proc_start:]
        skip_keywords = {'PROCEDURE', 'IDENTIFICATION', 'ENVIRONMENT', 'DATA', 'DIVISION'}
        for m in RE_PARAGRAPH.finditer(proc_source):
            para_name = m.group(1)
            if para_name.upper() in skip_keywords:
                continue
            para_line = proc_start + source[proc_start:m.start()+proc_start].count('\n') + 1
            functions.append({
                "name": para_name, "line_number": para_line, "end_line": para_line + 1,
                "args": [], "class_context": None, "function_calls": [],
                "lang": "cobol", "is_dependency": False,
            })

    # DATA items as variables
    for m in RE_DATA_ITEM.finditer(source):
        name = m.group(2)
        line = source[:m.start()].count('\n') + 1
        variables.append({"name": name, "line_number": line, "lang": "cobol"})

    # CALL statements
    for m in RE_CALL.finditer(source):
        call_name = m.group(1)
        call_line = source[:m.start()].count('\n') + 1
        calls.append({"name": call_name, "line_number": call_line, "lang": "cobol"})

    # COPY as imports
    for m in RE_COPY.finditer(source):
        copy_name = m.group(1)
        copy_line = source[:m.start()].count('\n') + 1
        imports.append({"name": copy_name, "source": copy_name, "line_number": copy_line, "lang": "cobol"})

    return {
        "path": path_str, "lang": "cobol", "is_dependency": False,
        "functions": functions, "classes": classes, "variables": variables,
        "imports": imports, "function_calls": calls,
        "language": "cobol", "extensions": list(COBOL_EXTENSIONS),
    }

def extract_cobol_symbols(file_path: str, content: str) -> Dict[str, Any]:
    """Backward compatibility: public wrapper around regex parser."""
    result = _parse_with_regex(content, file_path)
    symbols = []
    for c in result.get("classes", []):
        symbols.append({"name": c["name"], "type": "program",
                        "start_line": c["line_number"], "end_line": c["end_line"],
                        "is_exported": True, "children": []})
    for f in result.get("functions", []):
        fn = f.get("name", "")
        if "_DIVISION" in fn:
            symbols.append({"name": fn, "type": "division",
                            "start_line": f["line_number"], "end_line": f["end_line"],
                            "is_exported": False, "children": []})
        elif "SECTION" in fn or f.get("class_context"):
            symbols.append({"name": fn, "type": "section",
                            "start_line": f["line_number"], "end_line": f["end_line"],
                            "is_exported": False, "children": []})
        else:
            symbols.append({"name": fn, "type": "paragraph",
                            "start_line": f["line_number"], "end_line": f["end_line"],
                            "is_exported": False, "children": []})
    for v in result.get("variables", []):
        symbols.append({"name": v["name"], "type": "data_item",
                        "start_line": v["line_number"], "end_line": v["line_number"],
                        "is_exported": False, "level": None, "pic": None, "value": None})
    return {
        "symbols": symbols,
        "program_id": result["classes"][0]["name"] if result.get("classes") else None,
        "language": "cobol",
        "extensions": list(COBOL_EXTENSIONS),
    }

def parse_cobol(file_path: Path, **kwargs) -> Dict[str, Any]:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"error": "cannot_read_file", "lang": "cobol"}

    path_str = str(file_path)

    try:
        result = _parse_with_ts(content, path_str)
    except ImportError:
        result = _parse_with_regex(content, path_str)

    # Backward compat fields
    result["program_id"] = result["classes"][0]["name"] if result.get("classes") else None
    result["language"] = "cobol"
    result["extensions"] = list(COBOL_EXTENSIONS)
    return result
