"""
Shared State Detection — finds mutable global state, singletons, caches,
and class-level shared data that can cause side-effects and race conditions.

Detects:
1. Module-level mutable variables (lists, dicts, sets)
2. Singleton patterns (__new__ override, module instance)
3. In-memory caches (_cache = {}, @lru_cache)
4. Class-level mutable state
5. Mutable default arguments (def foo(x=[]))

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.State_analyzer
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CodeCortex.CodeAnalysis.StateAnalyzer")

MUTABLE_TYPES = {"list", "dict", "set", "{}", "[]", "set()", "list()", "dict()"}
SINGLETON_PATTERNS = [
    re.compile(r"__new__\s*\(.*cls.*\)"),
    re.compile(r"_instance\s*=\s*None"),
    re.compile(r"instance\s*=\s*None"),
]
CACHE_PATTERNS = [
    re.compile(r"_cache\s*[:=]"),
    re.compile(r"_cached?\s*[:=]"),
    re.compile(r"cache\s*=\s*\{\}"),
    re.compile(r"lru_cache"),
    re.compile(r"cache\.(get|set|put|delete)"),
]
MUTABLE_DEFAULT_PATTERN = re.compile(
    r"def\s+\w+\s*\([^)]*\b(\w+)\s*=\s*(\[\]|\{\}|list\(\)|dict\(\)|set\(\))\s*[,)]"
)


@dataclass
class SharedStateFinding:
    """A single instance of shared mutable state."""
    category: str  # global_var, singleton, cache, class_state, mutable_default
    file: str
    line: int
    name: str
    detail: str
    risk: str  # high, medium, low
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "name": self.name,
            "detail": self.detail,
            "risk": self.risk,
            "suggestion": self.suggestion,
        }


class StateAnalyzer:
    """Static analyzer for shared mutable state in Python codebases.

    Usage:
        analyzer = StateAnalyzer()
        result = analyzer.analyze("/path/to/repo")
    """

    def analyze(self, root_path: str, max_files: int = 2000) -> Dict[str, Any]:
        """Scan a codebase for shared state issues.

        Args:
            root_path: Root directory to scan.
            max_files: Maximum Python files to scan.

        Returns:
            Dict with findings summary and per-file details.
        """
        root = Path(root_path)
        if not root.exists():
            return {"error": f"Path not found: {root_path}"}

        all_findings: List[SharedStateFinding] = []
        files_scanned = 0

        for fp in root.rglob("*.py"):
            if not fp.is_file():
                continue
            if any(p.startswith(".") or p in ("node_modules", "venv", ".venv", "__pycache__") for p in fp.relative_to(root).parts):
                continue

            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            findings = self._analyze_file(fp, content)
            all_findings.extend(findings)

            files_scanned += 1
            if files_scanned >= max_files:
                break

        summary = self._build_summary(all_findings)
        return {
            "files_scanned": files_scanned,
            "total_findings": len(all_findings),
            "summary": summary,
            "findings": [f.to_dict() for f in all_findings],
        }

    def _analyze_file(self, fp: Path, content: str) -> List[SharedStateFinding]:
        """Analyze a single file for shared state issues."""
        findings: List[SharedStateFinding] = []
        lines = content.split("\n")

        findings.extend(self._find_global_mutable_vars(fp, lines))
        findings.extend(self._find_singletons(fp, content, lines))
        findings.extend(self._find_caches(fp, content, lines))
        findings.extend(self._find_class_state(fp, lines))
        findings.extend(self._find_mutable_defaults(fp, content))

        return findings

    def _find_global_mutable_vars(self, fp: Path, lines: List[str]) -> List[SharedStateFinding]:
        """Find module-level mutable variables."""
        findings = []
        in_class = False
        in_function = False
        indent_stack = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty, comments, imports
            if not stripped or stripped.startswith(("#", "import ", "from ")):
                continue

            # Track scope
            if stripped.startswith("class "):
                in_class = True
                indent_stack.append(len(line) - len(line.lstrip()))
                continue
            if stripped.startswith("def ") or stripped.startswith("async def "):
                in_function = True
                indent_stack.append(len(line) - len(line.lstrip()))
                continue

            indent = len(line) - len(line.lstrip())

            # Pop scope on dedent
            while indent_stack and indent <= indent_stack[-1]:
                indent_stack.pop()
                if not indent_stack:
                    in_class = False
                    in_function = False

            # Only check module-level (indent 0, not in class/function)
            if indent > 0 or in_class or in_function:
                continue

            # Detect mutable assignment: var = [] or var = {} or var = set()
            m = re.match(r"^(\w+)\s*=\s*(\[\]|\{\}|set\(\)|list\(\)|dict\(\))", stripped)
            if m:
                var_name = m.group(1)
                if not var_name.startswith("_"):
                    findings.append(SharedStateFinding(
                        category="global_var",
                        file=str(fp),
                        line=i + 1,
                        name=var_name,
                        detail=f"Module-level mutable variable '{var_name}' = {m.group(2)}",
                        risk="high",
                        suggestion=f"Encapsulate '{var_name}' in a class or use dataclass",
                    ))

        return findings

    def _find_singletons(self, fp: Path, content: str, lines: List[str]) -> List[SharedStateFinding]:
        """Find singleton pattern implementations."""
        findings = []

        # Pattern 1: __new__ override
        for i, line in enumerate(lines):
            if re.search(r"__new__\s*\(.*cls.*\)", line):
                # Check if there's an instance check
                for j in range(i, min(i + 15, len(lines))):
                    if "_instance" in lines[j] or "instance" in lines[j]:
                        findings.append(SharedStateFinding(
                            category="singleton",
                            file=str(fp),
                            line=i + 1,
                            name=Path(fp).stem,
                            detail="Singleton pattern via __new__ override",
                            risk="medium",
                            suggestion="Consider dependency injection instead of singleton",
                        ))
                        break

        # Pattern 2: Module-level _instance = None
        for i, line in enumerate(lines):
            m = re.match(r"^(_instance|instance)\s*=\s*None", line.strip())
            if m:
                # Check if there's a get_instance function
                for j in range(max(0, i - 3), min(i + 10, len(lines))):
                    if "get_instance" in lines[j] or "_instance" in lines[j]:
                        findings.append(SharedStateFinding(
                            category="singleton",
                            file=str(fp),
                            line=i + 1,
                            name=m.group(1),
                            detail="Singleton via module-level instance holder",
                            risk="medium",
                            suggestion="Use dependency injection framework",
                        ))
                        break

        return findings

    def _find_caches(self, fp: Path, content: str, lines: List[str]) -> List[SharedStateFinding]:
        """Find in-memory cache patterns."""
        findings = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            for pattern in CACHE_PATTERNS:
                if pattern.search(stripped):
                    risk = "high" if "={" in stripped else "medium"
                    findings.append(SharedStateFinding(
                        category="cache",
                        file=str(fp),
                        line=i + 1,
                        name=re.sub(r"[:\s=].*", "", stripped.split("#")[0]),
                        detail=stripped[:100],
                        risk=risk,
                        suggestion="Use TTL cache or redis instead of in-memory dict" if risk == "high" else "",
                    ))
                    break

        return findings

    def _find_class_state(self, fp: Path, lines: List[str]) -> List[SharedStateFinding]:
        """Find class-level mutable state shared across instances."""
        findings = []
        in_class = False
        class_indent = 0
        class_name = ""

        for i, line in enumerate(lines):
            stripped = line.strip()
            cm = re.match(r"^class\s+(\w+)", stripped)
            if cm:
                in_class = True
                class_indent = len(line) - len(line.lstrip())
                class_name = cm.group(1)
                continue

            if in_class:
                indent = len(line) - len(line.lstrip())
                if indent <= class_indent and stripped:
                    in_class = False
                    continue

                # Detect class-level mutable: var = []/{} (not in __init__)
                if re.match(r"^\s+(\w+)\s*=\s*(\[\]|\{\}|set\(\)|list\(\)|dict\(\))", stripped):
                    if "__init__" not in stripped:
                        var_name = re.match(r"\s+(\w+)", stripped).group(1)
                        if not var_name.startswith("_"):
                            findings.append(SharedStateFinding(
                                category="class_state",
                                file=str(fp),
                                line=i + 1,
                                name=f"{class_name}.{var_name}",
                                detail=f"Class-level mutable state shared across instances",
                                risk="high",
                                suggestion=f"Move '{var_name}' initialization to __init__",
                            ))

        return findings

    def _find_mutable_defaults(self, fp: Path, content: str) -> List[SharedStateFinding]:
        """Find mutable default argument values."""
        findings = []
        for m in MUTABLE_DEFAULT_PATTERN.finditer(content):
            param_name = m.group(1)
            default_val = m.group(2)
            line_num = content[:m.start()].count("\n") + 1
            findings.append(SharedStateFinding(
                category="mutable_default",
                file=str(fp),
                line=line_num,
                name=param_name,
                detail=f"Mutable default argument '{param_name}={default_val}'",
                risk="high",
                suggestion=f"Use `None` as default and assign inside function: if {param_name} is None: {param_name} = {default_val}",
            ))
        return findings

    def _build_summary(self, findings: List[SharedStateFinding]) -> Dict[str, Any]:
        """Build summary statistics."""
        by_category: Dict[str, int] = {}
        by_risk: Dict[str, int] = {}
        for f in findings:
            by_category[f.category] = by_category.get(f.category, 0) + 1
            by_risk[f.risk] = by_risk.get(f.risk, 0) + 1

        return {
            "by_category": by_category,
            "by_risk": by_risk,
            "categories": {
                "global_var": "Module-level mutable variables",
                "singleton": "Singleton patterns",
                "cache": "In-memory caches",
                "class_state": "Class-level shared state",
                "mutable_default": "Mutable default arguments",
            },
        }
