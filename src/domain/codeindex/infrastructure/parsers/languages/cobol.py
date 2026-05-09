"""
/**
 * @project   CodeCortex
 * @package   CodeIndex/Parsers/Languages
 * @standard  Aegis-CrossStack-v1.0
 * * COBOL parser — standalone regex-based processor (no tree-sitter).
 *   Extracts: programs, paragraphs, sections, data items, COPY statements.
 *   Ported from GitNexus's cobol-processor.ts and cobol-preprocessor.ts.
 */
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("CodeCortex.CodeIndex.Parsers.COBOL")

COBOL_EXTENSIONS = {'.cob', '.cbl', '.cobol', '.cpy', '.copybook'}
JCL_EXTENSIONS = {'.jcl', '.job', '.proc'}

# DIVISION patterns
RE_DIVISION = re.compile(
    r'(IDENTIFICATION|ID|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\.',
    re.IGNORECASE | re.MULTILINE
)
# SECTION pattern
RE_SECTION = re.compile(r'(\w[\w-]*)\s+SECTION\.', re.IGNORECASE | re.MULTILINE)
# PARAGRAPH pattern
RE_PARAGRAPH = re.compile(r'(\w[\w-]*)\.\s*$', re.MULTILINE)
# DATA item pattern (level number + name)
RE_DATA_ITEM = re.compile(
    r'(\d{2})\s+(\w[\w-]*)\s*(?:PIC\s+(\S+))?\s*(?:VALUE\s+(.+?))?\.',
    re.IGNORECASE | re.MULTILINE
)
# COPY statement
RE_COPY = re.compile(
    r'COPY\s+(\w[\w-]*(?:\/\w[\w-]*)*)\s*(?:REPLACING.*)?\.',
    re.IGNORECASE | re.MULTILINE
)
# CALL statement
RE_CALL = re.compile(
    r'CALL\s+[\'"](\w[\w-]*)',
    re.IGNORECASE | re.MULTILINE
)
# PROGRAM-ID
RE_PROGRAM_ID = re.compile(
    r'PROGRAM-ID\.\s*(\w[\w-]*)',
    re.IGNORECASE | re.MULTILINE
)


def is_cobol_file(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in COBOL_EXTENSIONS or ext in JCL_EXTENSIONS


def preprocess_cobol(source: str) -> str:
    """Remove comments, string literals, and normalize whitespace."""
    # Remove comment lines (asterisk or slash in column 7)
    lines = source.split('\n')
    cleaned = []
    for line in lines:
        if len(line) > 6 and line[6] in ('*', '/'):
            continue
        # Remove column 73+ (sequence area)
        if len(line) > 72:
            line = line[:72]
        cleaned.append(line.rstrip())
    return '\n'.join(cleaned)


def extract_cobol_symbols(file_path: str, content: str) -> Dict[str, Any]:
    """
    Extract symbols from COBOL source code.
    Returns structured parse result similar to TreeSitter parsers.
    """
    source = preprocess_cobol(content)
    symbols = []
    
    # 1. Find PROGRAM-ID
    prog_id = None
    m = RE_PROGRAM_ID.search(source)
    if m:
        prog_id = m.group(1)
        prog_line = source[:m.start()].count('\n') + 1
        symbols.append({
            "name": prog_id,
            "type": "program",
            "start_line": prog_line,
            "end_line": prog_line + 10,
            "is_exported": True,
            "children": []
        })
    
    # 2. Find DIVISIONs
    for m in RE_DIVISION.finditer(source):
        div_name = m.group(1).upper()
        div_line = source[:m.start()].count('\n') + 1
        if div_name in ('IDENTIFICATION', 'ID'):
            continue  # Skip boilerplate
        symbols.append({
            "name": f"{div_name}_DIVISION" if prog_id else div_name,
            "type": "division",
            "start_line": div_line,
            "end_line": div_line + 1,
            "is_exported": False,
            "children": []
        })
    
    # 3. Find SECTIONs
    for m in RE_SECTION.finditer(source):
        sec_name = m.group(1)
        sec_line = source[:m.start()].count('\n') + 1
        symbols.append({
            "name": sec_name,
            "type": "section",
            "start_line": sec_line,
            "end_line": sec_line + 1,
            "is_exported": False,
            "children": []
        })
    
    # 4. Find PARAGRAPHs (in PROCEDURE DIVISION)
    proc_div_start = source.upper().find('PROCEDURE DIVISION')
    if proc_div_start >= 0:
        proc_source = source[proc_div_start:]
        for m in RE_PARAGRAPH.finditer(proc_source):
            para_name = m.group(1)
            if para_name.upper() in ('PROCEDURE', 'IDENTIFICATION', 'ENVIRONMENT', 'DATA'):
                continue
            para_line = proc_div_start + source[proc_div_start:m.start()+proc_div_start].count('\n') + 1
            symbols.append({
                "name": para_name,
                "type": "paragraph",
                "start_line": para_line,
                "end_line": para_line + 1,
                "is_exported": False,
                "children": []
            })
    
    # 5. Find DATA items
    for m in RE_DATA_ITEM.finditer(source):
        level = int(m.group(1))
        name = m.group(2)
        pic = m.group(3) or ""
        value = m.group(4) or ""
        item_line = source[:m.start()].count('\n') + 1
        symbols.append({
            "name": name,
            "type": "data_item",
            "start_line": item_line,
            "end_line": item_line,
            "is_exported": False,
            "level": level,
            "pic": pic.strip(),
            "value": value.strip(),
        })
    
    # 6. Find CALL statements
    for m in RE_CALL.finditer(source):
        call_name = m.group(1)
        call_line = source[:m.start()].count('\n') + 1
        symbols.append({
            "name": call_name,
            "type": "call",
            "start_line": call_line,
            "end_line": call_line,
            "is_exported": False,
        })
    
    return {
        "symbols": symbols,
        "program_id": prog_id,
        "language": "cobol",
        "extensions": list(COBOL_EXTENSIONS),
    }


def parse_cobol(file_path: Path, **kwargs) -> Dict[str, Any]:
    """Parse a COBOL file and return structured symbols."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"error": "cannot_read_file"}
    
    return extract_cobol_symbols(str(file_path), content)
