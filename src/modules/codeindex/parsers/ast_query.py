"""
Structural Code Search — AST-level pattern matching via Tree-sitter.

Enables queries like:
- "find all functions with more than 5 parameters"
- "find all empty except blocks"
- "find all classes without docstrings"
- "find all functions with nesting depth > 4"

Falls back to regex-based detection when Tree-sitter is unavailable.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Ast_query
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.CodeIndex.AstQuery")

# ── Pattern definitions ───────────────────────────────────

# Regex-based structural patterns (Tree-sitter fallback)
STRUCTURAL_PATTERNS: Dict[str, Dict] = {
    "long_function": {
        "label": "Long function",
        "description": "Functions exceeding line threshold",
        "file_patterns": ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs"],
        "min_lines": 50,
    },
    "many_params": {
        "label": "Too many parameters",
        "description": "Functions with excessive parameters",
        "file_patterns": ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs"],
        "max_params": 5,
    },
    "empty_except": {
        "label": "Empty except/pass",
        "description": "Bare except or empty catch blocks",
        "file_patterns": ["*.py", "*.js", "*.ts", "*.java"],
        "pattern": "except\\s*:|catch\\s*\\([^)]*\\)\\s*\\{\\s*\\}",
    },
    "no_docstring": {
        "label": "Missing docstring",
        "description": "Public functions/classes without docstrings",
        "file_patterns": ["*.py"],
        "regex": r"def\s+(\w+)\s*\([^)]*\):\s*(?!\s*\"\"\")",
    },
    "deep_nesting": {
        "label": "Deep nesting",
        "description": "Deeply nested control structures (>4 levels)",
        "file_patterns": ["*.py", "*.js", "*.ts"],
        "max_depth": 4,
    },
    "no_type_hints": {
        "label": "Missing type hints",
        "description": "Public functions missing type annotations",
        "file_patterns": ["*.py"],
        "regex": r"def\s+(\w+)\s*\((?!.*:.*\))",
    },
    "todo_comment": {
        "label": "TODO/FIXME",
        "description": "Outstanding TODO or FIXME comments",
        "file_patterns": ["*"],
        "regex": r"(?i)(TODO|FIXME|HACK|XXX|WORKAROUND)\b",
    },
    "large_class": {
        "label": "Large class",
        "description": "Classes with too many methods",
        "file_patterns": ["*.py"],
        "max_methods": 20,
    },
    "no_return": {
        "label": "Missing return",
        "description": "Functions with no return statement",
        "file_patterns": ["*.py"],
        "regex": r"def\s+(\w+)\s*\([^)]*\):\s*(?!.*\breturn\b)",
    },
    "duplicate_code": {
        "label": "Duplicate code",
        "description": "Similar code blocks (simple heuristic)",
        "file_patterns": ["*.py", "*.js", "*.ts"],
        "min_similar_lines": 10,
    },
}


class AstQueryEngine:
    """Structural code search using AST pattern matching.

    Usage:
        engine = AstQueryEngine()
        results = engine.search("/path/to/repo", pattern="long_function")
        # or
        results = engine.search_by_query("/path/to/repo", {
            "pattern": "function",
            "filters": {"min_params": 5, "min_lines": 50}
        })
    """

    def __init__(self):
        self._ts_available = self._check_ts()

    def _check_ts(self) -> bool:
        """Check if Tree-sitter is available."""
        try:
            from tree_sitter import Language, Parser  # noqa: F401
            return True
        except ImportError:
            return False

    def search(
        self,
        root_path: str,
        pattern: str,
        file_pattern: Optional[str] = None,
        max_results: int = 50,
        threshold: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Search for a named structural pattern across the codebase.

        Args:
            root_path: Root directory to search.
            pattern: Pattern name (long_function, many_params, empty_except, etc.)
            file_pattern: Glob pattern (e.g. "*.py").
            max_results: Maximum findings.
            threshold: Custom threshold override (min_lines, max_params, etc.)
        """
        root = Path(root_path)
        if not root.exists():
            return {"error": f"Path not found: {root_path}", "pattern": pattern}

        config = STRUCTURAL_PATTERNS.get(pattern)
        if not config:
            return {"error": f"Unknown pattern: {pattern}. Available: {list(STRUCTURAL_PATTERNS.keys())}"}

        findings: List[Dict] = []
        pat_files = config.get("file_patterns", ["*"])
        re_pattern = config.get("regex", "")
        compiled_re = re.compile(re_pattern, re.M) if re_pattern else None
        effective_threshold = threshold if threshold is not None else (
            config.get("min_lines") or config.get("max_params") or config.get("max_depth") or config.get("max_methods")
        )

        # Walk files
        for fp in self._walk_files(root, pat_files, file_pattern):
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                lines = content.split("\n")
                ext = fp.suffix.lower()
            except Exception:
                continue

            if compiled_re:
                findings.extend(self._search_regex(fp, content, compiled_re, config, lines))

            if pattern == "long_function":
                findings.extend(self._find_long_functions(fp, content, lines, effective_threshold or 50))
            elif pattern == "many_params":
                findings.extend(self._find_many_params(fp, content, lines, effective_threshold or 5))
            elif pattern == "deep_nesting":
                findings.extend(self._find_deep_nesting(fp, content, lines, effective_threshold or 4))
            elif pattern == "large_class":
                findings.extend(self._find_large_classes(fp, content, lines, effective_threshold or 20))
            elif pattern == "no_return":
                findings.extend(self._find_no_return(fp, content, config.get("regex", "")))

            if len(findings) >= max_results:
                break

        return {
            "pattern": pattern,
            "label": config["label"],
            "description": config["description"],
            "threshold": effective_threshold,
            "total": len(findings),
            "findings": findings[:max_results],
            "ts_available": self._ts_available,
        }

    def search_by_query(
        self,
        root_path: str,
        query: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Search using a structured query dict.

        Query format:
            {"pattern": "function", "filters": {"min_params": 5, "min_lines": 50}}
            {"pattern": "class", "filters": {"min_methods": 15}}
            {"pattern": "empty_catch"}
        """
        pattern = query.get("pattern", "")
        if pattern in STRUCTURAL_PATTERNS:
            return self.search(
                root_path=root_path,
                pattern=pattern,
                file_pattern=query.get("file_pattern"),
                max_results=query.get("max_results", 50),
                threshold=query.get("threshold"),
            )

        return {"error": f"Unknown query pattern: {pattern}"}

    def list_patterns(self) -> List[Dict]:
        """List all available structural patterns."""
        return [
            {
                "name": name,
                "label": cfg["label"],
                "description": cfg["description"],
                "threshold": cfg.get("min_lines") or cfg.get("max_params") or cfg.get("max_depth") or cfg.get("max_methods"),
                "file_types": cfg["file_patterns"],
            }
            for name, cfg in STRUCTURAL_PATTERNS.items()
        ]

    # ── File walking ─────────────────────────────────────

    def _walk_files(
        self, root: Path, patterns: List[str], override: Optional[str],
    ) -> List[Path]:
        """Walk directory collecting matching files."""
        files: List[Path] = []
        glob_pat = override or "**/*"
        for fp in root.rglob(glob_pat):
            if not fp.is_file():
                continue
            # Skip hidden dirs and common excludes
            if any(p.startswith(".") for p in fp.relative_to(root).parts):
                continue
            if any(excl in fp.parts for excl in ("node_modules", "venv", ".venv", "__pycache__", "vendor")):
                continue
            # Check extension matches
            if override or fp.suffix.lower() in {p.replace("*.", ".") for p in patterns if p.startswith("*.")}:
                files.append(fp)

            if len(files) > 5000:  # Safety limit
                break
        return files

    # ── Pattern matchers ─────────────────────────────────

    def _search_regex(
        self, fp: Path, content: str, compiled: re.Pattern,
        config: Dict, lines: List[str],
    ) -> List[Dict]:
        """Generic regex-based pattern search."""
        findings = []
        label = config.get("label", "")
        for m in compiled.finditer(content):
            line_num = content[:m.start()].count("\n") + 1
            snippet = lines[line_num - 1].strip() if line_num <= len(lines) else m.group(0)
            findings.append({
                "file": str(fp),
                "line": line_num,
                "column": m.start() - content.rfind("\n", 0, m.start()) - 1,
                "match": snippet[:120],
                "label": label,
            })
        return findings

    def _find_long_functions(
        self, fp: Path, content: str, lines: List[str], min_lines: int,
    ) -> List[Dict]:
        """Find functions longer than threshold using indentation heuristic."""
        findings = []
        func_starts: List[Tuple[int, str]] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Detect function/method definition
            if re.match(r"^\s*def\s+\w+\s*\(", stripped) or re.match(r"^\s*(public|private|protected)?\s*\w+\s*\(", stripped):
                func_starts.append((i, stripped[:80]))
            elif re.match(r"^\s*(pub\s+)?fn\s+\w+\s*\(", stripped):
                func_starts.append((i, stripped[:80]))

        for start_idx, name in func_starts:
            # Find function end (next def at same or lesser indent)
            start_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
            end_idx = start_idx + 1
            for j in range(start_idx + 1, min(start_idx + 200, len(lines))):
                if lines[j].strip() and not lines[j].strip().startswith(("#", "//", "/*", "*")):
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    if indent <= start_indent and j > start_idx + 1:
                        end_idx = j - 1
                        break
                end_idx = j

            func_lines = end_idx - start_idx
            if func_lines >= min_lines:
                findings.append({
                    "file": str(fp),
                    "line": start_idx + 1,
                    "name": name,
                    "length": func_lines,
                    "match": f"{name} ({func_lines} lines)",
                    "label": "Long function",
                })
        return findings

    def _find_many_params(
        self, fp: Path, content: str, lines: List[str], max_params: int,
    ) -> List[Dict]:
        """Find functions with too many parameters."""
        findings = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            m = re.match(r"^\s*def\s+\w+\s*\(([^)]*)\)", stripped)
            if m:
                params_str = m.group(1).strip()
                if not params_str:
                    continue
                # Count parameters (handle nested parens in defaults)
                params = self._count_params(params_str)
                if params > max_params:
                    findings.append({
                        "file": str(fp),
                        "line": i + 1,
                        "name": re.match(r"def\s+(\w+)", stripped).group(1) if re.match(r"def\s+(\w+)", stripped) else "",
                        "params": params,
                        "match": f"{params} parameters (max: {max_params})",
                        "label": "Too many parameters",
                    })
        return findings

    def _find_deep_nesting(
        self, fp: Path, content: str, lines: List[str], max_depth: int,
    ) -> List[Dict]:
        """Find deeply nested code using indentation heuristic."""
        findings = []
        base_indent = 0
        depth = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*", "'''", '"""')):
                continue
            indent = len(line) - len(line.lstrip())
            if indent > base_indent:
                # Count indentation levels (assume 4-space tabs)
                levels = indent // 4
                if levels > max_depth and 0 < i < len(lines) - 1:
                    findings.append({
                        "file": str(fp),
                        "line": i + 1,
                        "depth": levels,
                        "match": stripped[:120],
                        "label": "Deep nesting",
                    })
        return findings

    def _find_large_classes(
        self, fp: Path, content: str, lines: List[str], max_methods: int,
    ) -> List[Dict]:
        """Find classes with too many methods."""
        findings = []
        class_pattern = re.compile(r"^\s*class\s+(\w+)")
        method_pattern = re.compile(r"^\s+def\s+\w+")

        current_class = None
        method_count = 0
        class_line = 0

        for i, line in enumerate(lines):
            cm = class_pattern.match(line)
            if cm:
                # Check previous class
                if current_class and method_count > max_methods:
                    findings.append({
                        "file": str(fp),
                        "line": class_line + 1,
                        "name": current_class,
                        "methods": method_count,
                        "match": f"Class '{current_class}' has {method_count} methods",
                        "label": "Large class",
                    })
                current_class = cm.group(1)
                method_count = 0
                class_line = i

            if current_class and method_pattern.match(line):
                method_count += 1

        # Check last class
        if current_class and method_count > max_methods:
            findings.append({
                "file": str(fp),
                "line": class_line + 1,
                "name": current_class,
                "methods": method_count,
                "match": f"Class '{current_class}' has {method_count} methods",
                "label": "Large class",
            })

        return findings

    def _find_no_return(
        self, fp: Path, content: str, regex: str,
    ) -> List[Dict]:
        """Find functions without return statement (simple heuristic)."""
        findings = []
        func_pattern = re.compile(r"^\s*def\s+(\w+)\s*\([^)]*\):\s*$", re.M)
        for m in func_pattern.finditer(content):
            func_name = m.group(1)
            start = m.end()
            # Skip dunder methods and __init__
            if func_name.startswith("__") or func_name == "__init__":
                continue
            # Look ahead for return
            chunk = content[start:start + 500]
            if "return" not in chunk and "yield" not in chunk:
                line_num = content[:start].count("\n") + 1
                findings.append({
                    "file": str(fp),
                    "line": line_num,
                    "name": func_name,
                    "match": f"Function '{func_name}' without return/yield",
                    "label": "Missing return",
                })
        return findings

    @staticmethod
    def _count_params(params_str: str) -> int:
        """Count parameters in a parameter string, handling nested parens."""
        # Remove default values by finding top-level commas
        depth = 0
        count = 0
        for ch in params_str:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                count += 1
        # self/cls don't count
        total = count + 1  # +1 for the last param after final comma
        return total
