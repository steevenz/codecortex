"""
Operational Layer — static execution path analysis and call chain tracing.

Provides runtime-like insights without actual execution:
- Entry-to-exit path enumeration
- Conditional branch analysis
- Call chain discovery from any function
- Hot path detection (most frequently called chains)

:project: CodeCortex
:package: Modules.Codeanalysis.Services.Operational
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.CodeAnalysis.Operational")


class ExecutionTracer:
    """Static execution path analysis.

    Traces possible execution paths through code without running it.
    Uses AST/call-graph data combined with control flow heuristics.

    Usage:
        tracer = ExecutionTracer()
        paths = tracer.trace_entry_to_exit("/path/to/app.py", "main")
        chain = tracer.get_call_chain("/path/to/app.py", "process_order")
    """

    def trace_entry_to_exit(
        self,
        file_path: str,
        entry_function: str,
        max_paths: int = 10,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """Trace all possible execution paths from entry to exit points.

        Args:
            file_path: Source file containing the entry function.
            entry_function: Name of the entry function.
            max_paths: Maximum number of paths to return.
            max_depth: Maximum call chain depth.

        Returns:
            Dict with paths, branches, exit_points, and complexity.
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
        except Exception as e:
            return {"error": str(e)}

        # Find the entry function boundaries
        func_info = self._find_function(content, entry_function)
        if not func_info:
            return {"error": f"Function '{entry_function}' not found in {file_path}"}

        func_lines = lines[func_info["start"]:func_info["end"]]
        func_content = "\n".join(func_lines)

        # Analyze control flow within the function
        branches = self._find_branches(func_content, func_info["start"])
        loops = self._find_loops(func_content, func_info["start"])
        calls = self._find_calls(func_content)
        exits = self._find_exits(func_content)

        # Enumerate paths (simplified: count combinations)
        path_count = self._estimate_paths(branches, loops)
        paths = self._build_sample_paths(
            func_content, branches, calls, exits, max_paths,
        )

        return {
            "function": entry_function,
            "file": file_path,
            "lines": f"{func_info['start'] + 1}-{func_info['end']}",
            "length": func_info["end"] - func_info["start"],
            "estimated_paths": path_count,
            "paths": paths[:max_paths],
            "branches": branches,
            "loops": loops,
            "internal_calls": calls,
            "exit_points": exits,
            "complexity": len(branches) + len(loops) + 1,  # Cyclomatic approx
        }

    def get_call_chain(
        self,
        file_path: str,
        function_name: str,
        max_depth: int = 5,
        direction: str = "forward",
    ) -> Dict[str, Any]:
        """Get the call chain starting from or ending at a function.

        Args:
            file_path: Source file.
            function_name: Function to trace from/to.
            max_depth: Maximum chain depth.
            direction: "forward" (calls made) or "backward" (callers).

        Returns:
            Dict with chain, depth, and unique call paths.
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}

        chain: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        self._build_chain(content, function_name, chain, visited, max_depth, 0, direction)

        return {
            "root": function_name,
            "file": file_path,
            "direction": direction,
            "depth": len(chain),
            "chain": chain,
            "unique_calls": len(visited),
        }

    def analyze_hot_path(
        self,
        repo_path: str,
        entry_points: List[str],
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """Analyze most frequently used execution paths across entry points.

        Args:
            repo_path: Repository root.
            entry_points: List of (file, function) entry points.
            max_depth: Max chain depth.

        Returns:
            Dict with call_frequency, shared_paths, and hot_paths.
        """
        root = Path(repo_path)
        all_calls: Dict[str, int] = {}

        for ep_file, ep_func in [ep.split("::") for ep in entry_points]:
            fp = root / ep_file if not Path(ep_file).is_absolute() else Path(ep_file)
            result = self.get_call_chain(str(fp), ep_func, max_depth)
            for item in result.get("chain", []):
                name = item.get("name", "")
                all_calls[name] = all_calls.get(name, 0) + 1

        sorted_calls = sorted(all_calls.items(), key=lambda x: x[1], reverse=True)
        return {
            "hot_functions": [
                {"name": name, "entry_points": count}
                for name, count in sorted_calls[:20]
            ],
            "call_frequency": all_calls,
            "shared_across": len(entry_points),
        }

    def _find_function(self, content: str, name: str) -> Optional[Dict]:
        """Find a function definition in source code."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if re.match(r"^\s*(?:async\s+)?def\s+" + re.escape(name) + r"\s*\(", line):
                start = i
                # Find function end
                indent = len(line) - len(line.lstrip())
                end = start + 1
                for j in range(start + 1, min(start + 300, len(lines))):
                    stripped = lines[j].strip()
                    if not stripped:
                        continue
                    next_indent = len(lines[j]) - len(lines[j].lstrip())
                    if next_indent <= indent and (
                        stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("@")
                    ):
                        end = j
                        break
                    end = j + 1

                return {"start": start, "end": end, "name": name, "line": i + 1}
        return None

    def _find_branches(self, content: str, offset: int) -> List[Dict]:
        """Find conditional branches (if/elif/else, ternary)."""
        branches = []
        for m in re.finditer(r"^\s*(if|elif|else)\b", content, re.M):
            branches.append({
                "type": m.group(1),
                "line": offset + content[:m.start()].count("\n") + 1,
                "condition": content[m.end():content.index(":", m.end())].strip()[:80],
            })
        return branches

    def _find_loops(self, content: str, offset: int) -> List[Dict]:
        """Find loop constructs (for, while)."""
        loops = []
        for m in re.finditer(r"^\s*(for|while)\b", content, re.M):
            loops.append({
                "type": m.group(1),
                "line": offset + content[:m.start()].count("\n") + 1,
                "condition": content[m.end():content.index(":", m.end())].strip()[:80],
            })
        return loops

    def _find_calls(self, content: str) -> List[Dict]:
        """Find internal function calls (not self, not builtins)."""
        calls = []
        skip = {"self", "cls", "super", "print", "len", "str", "int", "list", "dict",
                "set", "type", "isinstance", "hasattr", "getattr", "range", "open",
                "enumerate", "zip", "map", "filter", "sorted", "reversed", "min", "max",
                "sum", "any", "all", "abs", "round", "format", "repr", "import"}

        for m in re.finditer(r"\b([a-z_]\w*)\s*\(", content):
            name = m.group(1)
            if name not in skip and not name.startswith("_"):
                line_num = content[:m.start()].count("\n") + 1
                args_match = re.search(r"\(([^)]*)\)", content[m.start():])
                args = args_match.group(1)[:80] if args_match else ""
                calls.append({
                    "name": name,
                    "line": line_num,
                    "args": args,
                })
        return calls

    def _find_exits(self, content: str) -> List[Dict]:
        """Find exit/return points in the function body."""
        exits = []
        for m in re.finditer(r"^\s*(return|yield|raise)\b", content, re.M):
            line_num = content[:m.start()].count("\n") + 1
            value = content[m.end():content.index("\n", m.end())].strip()[:80] if "\n" in content[m.end():] else ""
            exits.append({
                "type": m.group(1),
                "line": line_num,
                "value": value,
            })
        return exits

    def _estimate_paths(self, branches: List, loops: List) -> int:
        """Estimate number of possible execution paths."""
        # Each if doubles paths (roughly), loops add 2 paths
        n_branches = len([b for b in branches if b["type"] != "else"])
        n_loops = len(loops)
        return max(1, 2 ** n_branches + n_loops)

    def _build_sample_paths(
        self, content: str, branches: List, calls: List, exits: List, max_paths: int,
    ) -> List[Dict]:
        """Build sample execution path descriptions."""
        paths = []
        # Path 1: happy path (first branch, no errors)
        path_1 = ["entry"]
        for b in branches[:3]:
            if b["type"] == "if":
                path_1.append(f"branch: {b['condition'][:40]}")
            elif b["type"] == "elif":
                break  # Skip alternatives in happy path
        if calls:
            path_1.append(f"call: {calls[0]['name']}")
        if exits:
            path_1.append(f"exit: {exits[0]['type']}")
        paths.append({"type": "happy_path", "steps": path_1})

        # Path 2: error path (if there's an error/exception path)
        error_branches = [b for b in branches if "error" in b.get("condition", "").lower()
                          or "fail" in b.get("condition", "").lower()
                          or "except" in b.get("type", "")]
        if error_branches:
            path_2 = ["entry"]
            path_2.append(f"branch: {error_branches[0]['condition'][:40]}")
            path_2.append("exit: raise/return error")
            paths.append({"type": "error_path", "steps": path_2})

        # Path 3: loop path
        if any(b["type"] in ("for", "while") for b in branches):
            paths.append({"type": "loop_path", "steps": ["entry", "loop iteration → ...", "exit"]})

        return paths[:max_paths]

    def _build_chain(
        self, content: str, func_name: str,
        chain: List, visited: Set[str], max_depth: int,
        depth: int, direction: str,
    ) -> None:
        """Recursively build call chain."""
        if depth >= max_depth or func_name in visited:
            return
        visited.add(func_name)

        calls = self._find_calls(content)
        entry = {"name": func_name, "depth": depth, "calls": []}

        for call in calls:
            if call["name"] not in visited:
                entry["calls"].append(call["name"])
                if depth + 1 < max_depth:
                    self._build_chain(
                        content, call["name"], chain, visited,
                        max_depth, depth + 1, direction,
                    )

        chain.append(entry)
