"""
Data Flow Tracing — variable-level data flow analysis across function boundaries.

Tracks how data moves through code: function inputs → transformations → outputs.
Enables AI coders to understand "where does this variable come from?"
and "what touches this data?"

Builds on graph_query(trace_flow) with additional variable-level analysis.

:project: CodeCortex
:package: Modules.Codeanalysis.Services.Tracing
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.CodeAnalysis.Tracing")


class DataFlowTrace:
    """Variable-level data flow tracing.

    Usage:
        tracer = DataFlowTrace()
        result = tracer.trace_variable("/path/to/file.py", "user_id", line=42)
        # {"variable": "user_id", "sources": [...], "sinks": [...], "transformations": [...]}
    """

    def trace_variable(
        self,
        file_path: str,
        variable_name: str,
        line: Optional[int] = None,
        max_hops: int = 5,
    ) -> Dict[str, Any]:
        """Trace where a variable comes from and where it goes.

        Args:
            file_path: Source file containing the variable.
            variable_name: Variable name to trace.
            line: Line number for disambiguation.
            max_hops: Max assignment/call chain length.

        Returns:
            Dict with sources, sinks, transformations, and flow path.
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
        except Exception as e:
            return {"error": str(e)}

        # Find the variable definition/assignment
        definition = self._find_definition(content, variable_name, line)

        # Trace backward (sources) and forward (sinks)
        sources = self._trace_backward(content, variable_name, definition, max_hops)
        sinks = self._trace_forward(content, variable_name, definition, max_hops)
        transformations = self._find_transformations(content, variable_name, definition)

        return {
            "variable": variable_name,
            "file": file_path,
            "definition": definition,
            "sources": sources,
            "sinks": sinks,
            "transformations": transformations,
            "flow_path": self._build_flow(definition, sources, sinks, transformations),
        }

    def trace_function_param(
        self,
        file_path: str,
        param_name: str,
        function_name: str,
        max_hops: int = 5,
    ) -> Dict[str, Any]:
        """Trace a function parameter: where it's called from and how it's used."""
        return self.trace_variable(file_path, param_name, max_hops=max_hops)

    def trace_api_data(
        self,
        file_path: str,
        endpoint: str,
        method: str = "GET",
    ) -> Dict[str, Any]:
        """Trace data flow through an API endpoint:
        request → handler → response.
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}

        # Detect framework and extract handler params
        result: Dict[str, Any] = {
            "endpoint": f"{method} {endpoint}",
            "file": file_path,
            "request_params": [],
            "data_sources": [],
            "response_path": [],
        }

        # FastAPI: request parameter, db session, response_model
        for m in re.finditer(
            r"async\s+def\s+\w+\s*\([^)]*request[^)]*\)",
            content, re.I,
        ):
            result["request_params"].append({"name": "request", "source": "http"})
        for m in re.finditer(
            r"async\s+def\s+\w+\s*\([^)]*db[^)]*\)", content, re.I,
        ):
            result["data_sources"].append({"name": "db", "type": "database"})

        # Express: req, res params
        for m in re.finditer(
            r"(?:app|router)\.(?:get|post|put|delete)\s*\([^)]*req[^)]*res[^)]*",
            content, re.I,
        ):
            result["request_params"].append({"name": "req", "source": "http"})
            result["response_path"].append({"name": "res", "type": "response"})

        return result

    def _find_definition(
        self, content: str, var: str, line: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Find where a variable is defined/assigned."""
        lines = content.split("\n")

        if line:
            # Check specific line
            idx = line - 1
            if 0 <= idx < len(lines):
                defn = self._parse_assignment(lines[idx], var)
                if defn:
                    return {**defn, "line": line}

        # General search
        for i, l in enumerate(lines):
            defn = self._parse_assignment(l, var)
            if defn:
                return {**defn, "line": i + 1}

        return None

    def _parse_assignment(self, line: str, var: str) -> Optional[Dict]:
        """Parse a variable assignment from a line of code."""
        stripped = line.strip()

        # var = value
        m = re.match(
            r"^(?:self\.)?"
            + re.escape(var)
            + r"\s*[:=]=\s*(.+?)(?:\s*#.*)?$", stripped,
        )
        if m:
            return {"type": "assignment", "value": m.group(1).strip()}

        # var: Type = value
        m = re.match(
            r"^(?:self\.)?" + re.escape(var) + r"\s*:\s*\w+\s*=\s*(.+?)(?:\s*#.*)?$",
            stripped,
        )
        if m:
            return {"type": "typed_assignment", "value": m.group(1).strip()}

        # for var in iterable:
        m = re.match(r"^for\s+" + re.escape(var) + r"\s+in\s+(.+?):", stripped)
        if m:
            return {"type": "loop_variable", "value": m.group(1).strip()}

        # def func(var: type)
        m = re.match(
            r"^def\s+\w+\s*\([^)]*\b" + re.escape(var) + r"\b", stripped,
        )
        if m:
            return {"type": "parameter", "value": "caller"}

        # var = await func()
        m = re.match(
            r"^(?:self\.)?" + re.escape(var) + r"\s*=\s*await\s+(.+?)(?:\s*#.*)?$",
            stripped,
        )
        if m:
            return {"type": "async_assignment", "value": m.group(1).strip()}

        return None

    def _trace_backward(
        self, content: str, var: str, definition: Optional[Dict],
        max_hops: int,
    ) -> List[Dict[str, Any]]:
        """Trace where a variable's value originates (backward)."""
        sources = []
        if not definition:
            return sources

        value = definition.get("value", "")
        if not value or value == "caller":
            return sources

        # Value is a literal → source is literal
        if re.match(r"^[\d\"'`\[]", value):
            sources.append({
                "type": "literal",
                "value": value[:100],
                "hops": 0,
            })
            return sources

        # Value is another variable
        var_match = re.match(r"^(\w+)", value)
        if var_match:
            other_var = var_match.group(1)
            sources.append({
                "type": "variable",
                "name": other_var,
                "hops": 0,
            })
            # Recursive trace
            if max_hops > 1:
                nested = self._find_definition(content, other_var, None)
                if nested:
                    deeper = self._trace_backward(content, other_var, nested, max_hops - 1)
                    sources.extend(deeper)

        # Value is a function call
        func_match = re.match(r"^(\w+)\((.+)?\)", value)
        if func_match:
            func_name = func_match.group(1)
            args = func_match.group(2) if func_match.lastindex and func_match.group(2) else ""
            sources.append({
                "type": "function_call",
                "function": func_name,
                "args": args[:100],
                "hops": 0,
            })
            # Trace arg variables
            if args and max_hops > 1:
                for arg_var in re.findall(r"\b([a-z_]\w*)\b", args):
                    if arg_var not in ("self", "cls", "None", "True", "False"):
                        arg_def = self._find_definition(content, arg_var, None)
                        if arg_def:
                            sources.extend(
                                self._trace_backward(content, arg_var, arg_def, max_hops - 1)
                            )

        return sources

    def _trace_forward(
        self, content: str, var: str, definition: Optional[Dict],
        max_hops: int,
    ) -> List[Dict[str, Any]]:
        """Trace where a variable is used (forward, within same function)."""
        sinks = []
        if not definition:
            return sinks

        def_line = definition.get("line", 0)
        lines = content.split("\n")

        function_end = self._find_function_end(lines, def_line)
        if not function_end:
            function_end = min(def_line + 30, len(lines))

        for i in range(def_line, function_end):
            line = lines[i].strip()

            # var as argument to function call: func(var)
            for m in re.finditer(r"\b(\w+)\s*\(\s*[^)]*\b" + re.escape(var) + r"\b[^)]*\)", line):
                sinks.append({
                    "type": "argument",
                    "function": m.group(1),
                    "line": i + 1,
                    "code": line[:100],
                })

            # var used in expression: return var, x = var + 1
            if re.search(r"(?:^|\s)" + re.escape(var) + r"(?:\s|$|[,)])", line):
                if f"={var}" not in line.replace(" ", "") and f":{var}" not in line.replace(" ", ""):
                    if var in line and not line.strip().startswith("#"):
                        sinks.append({
                            "type": "usage",
                            "line": i + 1,
                            "code": line[:100],
                        })

        return sinks

    def _find_transformations(
        self, content: str, var: str, definition: Optional[Dict],
    ) -> List[Dict[str, Any]]:
        """Find transformations applied to the variable."""
        transforms = []
        if not definition:
            return transforms

        def_line = definition.get("line", 0)
        lines = content.split("\n")
        function_end = self._find_function_end(lines, def_line) or len(lines)

        for i in range(def_line, function_end):
            line = lines[i].strip()

            # var = func(var) or var = var.transform()
            if re.match(
                r"^\s*" + re.escape(var) + r"\s*=\s*(?:\w+\.)*\w+\s*\(",
                line,
            ):
                transforms.append({
                    "type": "reassignment",
                    "code": line[:100],
                    "line": i + 1,
                })

            # var.method() calls
            for m in re.finditer(
                re.escape(var) + r"\.(\w+)\s*\(", line,
            ):
                transforms.append({
                    "type": "method_call",
                    "method": m.group(1),
                    "code": line[:100],
                    "line": i + 1,
                })

        return transforms

    def _build_flow(
        self,
        definition: Optional[Dict],
        sources: List[Dict],
        sinks: List[Dict],
        transforms: List[Dict],
    ) -> List[str]:
        """Build a human-readable data flow path."""
        flow = []
        for s in sources:
            t = s.get("type", "")
            v = s.get("value") or s.get("name") or s.get("function", "")
            flow.append(f"← {t}: {v}")
        if definition:
            flow.append(f"● {definition.get('type', 'variable')}")
        for t in transforms:
            flow.append(f"→ {t['type']}: {t.get('code', '')[:60]}")
        for s in sinks:
            flow.append(f"→ {s['type']}: {s.get('function', '') or s.get('code', '')[:60]}")
        return flow

    @staticmethod
    def _find_function_end(lines: List[str], start_line: int) -> Optional[int]:
        """Find the end of the function containing start_line."""
        # Find the function definition line
        func_start = None
        for i in range(start_line, -1, -1):
            if re.match(r"^\s*(?:async\s+)?def\s+\w+\s*\(", lines[i]):
                func_start = i
                break
        if func_start is None:
            return None

        # Find next def at same or lesser indent
        func_indent = len(lines[func_start]) - len(lines[func_start].lstrip())
        for i in range(func_start + 1, min(func_start + 300, len(lines))):
            stripped = lines[i].strip()
            if not stripped or stripped.startswith(("#", "'''", '"""')):
                continue
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= func_indent and (stripped.startswith("def ") or stripped.startswith("class ")):
                return i
            if stripped.startswith("@") and indent == func_indent:
                return i

        return min(func_start + 100, len(lines))
