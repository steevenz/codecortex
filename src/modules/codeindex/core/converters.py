"""
TreeSitter-to-Symbol converter – Single Responsibility:
Convert TreeSitterParser output dicts into RawSymbol DTOs for SQLite ingestion,
preserving graph-backend rich data for downstream graph sync.

:project: CodeCortex
:package: Modules.Codeindex.Core.Converters
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

from typing import List, Dict, Any
from src.modules.codeindex.parsers.strategies.base import RawSymbol

def _build_code_ref(
    file_rel_path: str,
    symbol_type: str,
    name: str,
    start_line: int,
    qualifier: str | None = None,
) -> str:
    qualified = f"{qualifier}.{name}" if qualifier else name
    safe_line = start_line if isinstance(start_line, int) and start_line > 0 else 1
    return f"{file_rel_path}:{symbol_type}:{qualified}@{safe_line}"

def parsed_data_to_raw_symbols(file_rel_path: str, parsed: Dict[str, Any]) -> List[RawSymbol]:
    """
    Convert TreeSitterParser output into RawSymbol list for SQLite symbols table.

    Preserves variables, imports, and function_calls in the RawSymbol fields so
    downstream graph sync can access them without re-parsing.
    """
    symbols: List[RawSymbol] = []
    lang = parsed.get("lang", "unknown")

    # Attach rich metadata to a sentinel "file" symbol so nothing is lost
    meta = {
        "language": lang,
        "frameworks": parsed.get("frameworks", []),
    }
    file_symbol = RawSymbol(
        name="__file__",
        symbol_type="file",
        start_line=1,
        end_line=1,
        code_ref=_build_code_ref(file_rel_path, "file", "__file__", 1),
        variables=parsed.get("variables", []),
        function_calls=parsed.get("function_calls", []),
        imports=parsed.get("imports", []),
        language=lang,
    )
    symbols.append(file_symbol)

    # Build class code_ref lookup for parent_id resolution
    class_code_refs: Dict[str, str] = {}
    for cls in parsed.get("classes", []):
        start_line = cls.get("line_number", 1)
        code_ref = _build_code_ref(file_rel_path, "class", cls["name"], start_line)
        class_code_refs[cls["name"]] = code_ref
        symbols.append(RawSymbol(
            name=cls["name"],
            symbol_type="class",
            start_line=start_line,
            end_line=cls.get("end_line", start_line),
            code_ref=code_ref,
            docstring=cls.get("docstring"),
            signature=",".join(cls.get("bases", [])),
            language=lang,
        ))

    for fn in parsed.get("functions", []):
        start_line = fn.get("line_number", 1)
        class_context = fn.get("class_context") or fn.get("context") if fn.get("context_type") == "class" else None
        symbol_type = "method" if class_context else "function"
        code_ref = _build_code_ref(file_rel_path, symbol_type, fn["name"], start_line, qualifier=class_context)
        signature = "(" + ",".join(fn.get("args", [])) + ")" if fn.get("args") else None
        parent_id = class_code_refs.get(class_context) if class_context else None
        symbols.append(RawSymbol(
            name=fn["name"],
            symbol_type=symbol_type,
            start_line=start_line,
            end_line=fn.get("end_line", start_line),
            code_ref=code_ref,
            parent_id=parent_id,
            docstring=fn.get("docstring"),
            signature=signature,
            function_calls=fn.get("function_calls", []),
            language=lang,
        ))

    return symbols
