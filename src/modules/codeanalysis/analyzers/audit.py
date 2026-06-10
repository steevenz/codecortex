"""
CodeAuditor - Source code security and quality auditor.

This module provides comprehensive code auditing capabilities including:
- Secret detection (API keys, tokens, credentials)
- PII detection (emails, SSNs, etc.)
- Configuration issue detection
- Vulnerability pattern detection
- Comment tag detection (TODO, FIXME, XXX, HACK, etc.)
- N+1 query detection
- Empty function/class detection
- Unclosed bracket/tag detection
- HTML/XML tag validation

Supported Comment Tags for Detection:
-------------------------------------
- TODO: Task to be completed (priority: high)
- FIXME: Bug that needs fixing (priority: critical)
- XXX: Deprecated/obsolete code (priority: high)
- HACK: Temporary workaround (priority: medium)
- WARN: Warning about potential issues (priority: medium)
- NOTE: Important information (priority: low)
- WIP: Work in progress (priority: medium)
- STUB: Placeholder implementation (priority: high)
- REVIEW: Code needs review (priority: medium)
- OPTIMIZE: Performance optimization needed (priority: low)
- DEPRECATED: Deprecated code (priority: medium)
- BUG: Known bug (priority: critical)
- UNDONE: Reverts a previous change (priority: medium)
- REVIEW: Code needs review (priority: medium)
- CONSIDER: Consider alternative approach (priority: medium)
- QUESTION: Unanswered question (priority: medium)

Configuration:
--------------
To add new tags, extend TAG_PATTERNS list with:
{
    "tag": "YOUR_TAG",
    "pattern": r"(?i)\\bYOUR_TAG\\b",
    "priority": "high",  # critical, high, medium, low
    "description": "Description of what this tag means",
    "comment_styles": ["line", "block", "docstring"]  # Optional filter
}

Output Format:
--------------
- JSON: Structured output with full metadata
- CSV: Tabular format for spreadsheet analysis
- Report: Human-readable summary

Usage:
------
    auditor = CodeAuditor.audit({
        "target_path": "/path/to/code",
        "scan_categories": ["comments", "structure", "empty_code", "nplus1"],
        "output_format": "json"
    }).

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.Audit
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import os
import re
import json
import csv
import fnmatch
import logging
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

def _log_structured(event: str, **kwargs):
    import json
    from datetime import datetime, timezone
    entry = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    logger.info(json.dumps(entry))

class Priority(Enum):
    """Priority levels for findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class FindingType(Enum):
    """Types of findings that can be detected."""
    COMMENT_TAG = "comment_tag"
    SECRET = "secret"
    PII = "pii"
    MISCONFIG = "misconfig"
    VULNERABILITY = "vulnerability"
    NPLUS1 = "nplus1"
    EMPTY_FUNCTION = "empty_function"
    EMPTY_CLASS = "empty_class"
    UNCLOSED_BRACKET = "unclosed_bracket"
    UNCLOSED_HTML_TAG = "unclosed_html_tag"

COMMENT_TAG_CONFIG: List[Dict[str, Any]] = [
    {
        "tag": "TODO",
        "pattern": r"(?i)\bTODO\s*:",
        "priority": Priority.HIGH.value,
        "description": "Task to be completed",
        "aliases": ["todo", "Todo", "tODo"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "FIXME",
        "pattern": r"(?i)\bFIXME\s*:",
        "priority": Priority.CRITICAL.value,
        "description": "Bug that needs fixing",
        "aliases": ["fixme", "Fixme", "fIXME"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "XXX",
        "pattern": r"(?i)\bXXX\s*:",
        "priority": Priority.HIGH.value,
        "description": "Deprecated or obsolete code",
        "aliases": ["xxx", "Xxx", "xXX"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "HACK",
        "pattern": r"(?i)\bHACK\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Temporary workaround - technical debt",
        "aliases": ["hack", "Hack"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "WARN",
        "pattern": r"(?i)\bWARN\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Warning about potential issues",
        "aliases": ["warn", "Warn"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "NOTE",
        "pattern": r"(?i)\bNOTE\s*:",
        "priority": Priority.LOW.value,
        "description": "Important information",
        "aliases": ["note", "Note"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "WIP",
        "pattern": r"(?i)\bWIP\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Work in progress",
        "aliases": ["wip", "Wip"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "STUB",
        "pattern": r"(?i)\bSTUB\s*:",
        "priority": Priority.HIGH.value,
        "description": "Placeholder implementation - needs completion",
        "aliases": ["stub", "Stub"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "REVIEW",
        "pattern": r"(?i)\bREVIEW\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Code needs review",
        "aliases": ["review", "Review"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "OPTIMIZE",
        "pattern": r"(?i)\bOPTIMIZE\s*:",
        "priority": Priority.LOW.value,
        "description": "Performance optimization needed",
        "aliases": ["optimize", "Optimize"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "DEPRECATED",
        "pattern": r"(?i)\bDEPRECATED\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Deprecated code",
        "aliases": ["deprecated", "Deprecated"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "BUG",
        "pattern": r"(?i)\bBUG\s*:",
        "priority": Priority.CRITICAL.value,
        "description": "Known bug",
        "aliases": ["bug", "Bug"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "UNDONE",
        "pattern": r"(?i)\bUNDONE\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Reverts a previous change",
        "aliases": ["undone", "Undone"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "CONSIDER",
        "pattern": r"(?i)\bCONSIDER\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Consider alternative approach",
        "aliases": ["consider", "Consider"],
        "comment_styles": ["line", "block", "docstring"],
    },
    {
        "tag": "QUESTION",
        "pattern": r"(?i)\bQUESTION\s*:",
        "priority": Priority.MEDIUM.value,
        "description": "Unanswered question",
        "aliases": ["question", "Question"],
        "comment_styles": ["line", "block", "docstring"],
    },
]

TAG_PATTERNS = COMMENT_TAG_CONFIG

@dataclass
class CodeFinding:
    """Represents a code finding with full context."""
    type: str
    severity: str
    line: int
    column: int
    message: str
    file: str
    details: Dict[str, Any] = field(default_factory=dict)
    context: str = ""
    confidence: float = 1.0

@dataclass
class CommentTag:
    """Represents a detected comment tag with full context."""
    tag: str
    priority: str
    line: int
    column: int
    message: str
    file: str
    author: Optional[str] = None
    last_modified: Optional[str] = None
    context: str = ""
    confidence: float = 1.0
    comment_type: str = "line"

@dataclass
class AuditResult:
    """Container for complete audit results."""
    target: str
    scan_categories: List[str]
    scanned_files: int
    summary: Dict[str, int]
    findings: Dict[str, List[Dict[str, Any]]]
    recommendations: Dict[str, Any]
    errors: List[Dict[str, str]]

class CodeAuditor:
    """
    Source code security and quality auditor.

    Detects secrets, PII, misconfigurations, vulnerabilities, and comment tags
    across multiple programming languages and comment styles.

    Integrates with CodeAnalyzer for AST-based analysis to avoid re-parsing
    and provide more accurate findings.
    """

    DEFAULT_EXCLUDE_PATTERNS: Set[str] = {
        "node_modules", "dist", "build", "target", ".git", ".svn",
        "*.min.js", "*.min.css", "*.pyc", "__pycache__", ".venv", "venv",
        "tests/fixtures", "test/fixtures", "mock", "stub", "fake",
    }

    SUPPORTED_EXTENSIONS: Set[str] = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb", ".php",
        ".swift", ".kt", ".scala", ".cs", ".cpp", ".c", ".h", ".hpp", ".m", ".mm",
        ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
        ".yml", ".yaml", ".json", ".xml", ".toml", ".ini", ".cfg", ".conf",
        ".env", ".md", ".rst", ".txt", ".html", ".css", ".scss", ".sql",
        ".dockerfile", ".gitignore", ".gitattributes",
        ".vue", ".svelte", ".astro", ".ejs", ".haml", ".slim",
        ".gradle", ".sbt", ".clj", ".cljs", ".ex", ".exs",
        ".pl", ".pm", ".lua", ".r",
        ".tf", ".hcl", ".helmignore",
    }

    COMMENT_STYLES: Dict[str, Dict[str, Optional[str]]] = {
        "python": {"line": "#", "block": '"""', "docstring": '"""'},
        "javascript": {"line": "//", "block": "/*", "docstring": None},
        "typescript": {"line": "//", "block": "/*", "docstring": None},
        "java": {"line": "//", "block": "/*", "docstring": None},
        "csharp": {"line": "//", "block": "/*", "docstring": None},
        "go": {"line": "//", "block": "/*", "docstring": None},
        "rust": {"line": "//", "block": "/*", "docstring": None},
        "ruby": {"line": "#", "block": "=begin", "docstring": None},
        "php": {"line": "//", "block": "/*", "docstring": None},
        "shell": {"line": "#", "block": None, "docstring": None},
        "sql": {"line": "--", "block": "/*", "docstring": None},
    }

    @classmethod
    def _load_aiignore_patterns(cls, repo_path: str) -> Set[str]:
        """Load exclude patterns from .aiignore file."""
        patterns = set(cls.DEFAULT_EXCLUDE_PATTERNS)
        aiignore_path = Path(repo_path) / ".aiignore"
        if aiignore_path.exists():
            try:
                content = aiignore_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.add(line)
            except Exception:
                pass
        return patterns

    @classmethod
    def _should_exclude_file(cls, file_path: str, patterns: Set[str]) -> bool:
        """Check if file should be excluded based on patterns."""
        import fnmatch
        file_path_lower = file_path.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(file_path_lower, pattern.lower()):
                return True
            if fnmatch.fnmatch(Path(file_path).name, pattern.lower()):
                return True
        return False

    @classmethod
    def _get_cached_symbols(cls, db_path: str, file_path: str) -> Optional[List[Dict]]:
        """Get symbols from CodeAnalyzer cache if available."""
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name, kind, line_start, line_end, signature, docstring FROM symbols WHERE file_id = (SELECT id FROM files WHERE path = ?)",
                (file_path,)
            )
            symbols = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return symbols if symbols else None
        except Exception:
            return None

    @classmethod
    def _analyze_empty_from_ast(cls, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze empty functions/classes from cached AST symbols."""
        findings: List[Dict[str, Any]] = []
        for sym in symbols:
            if sym.get("kind") == "function":
                if sym.get("line_end", 0) - sym.get("line_start", 0) <= 1:
                    if "pass" in sym.get("signature", "") or not sym.get("docstring"):
                        findings.append({
                            "type": "empty_function",
                            "severity": "medium",
                            "line": sym["line_start"],
                            "message": f"Empty function '{sym['name']}' has no implementation",
                            "file": "",
                            "details": {"function_name": sym["name"]},
                            "context": sym.get("signature", ""),
                            "confidence": 0.95,
                        })
            elif sym.get("kind") == "class":
                if sym.get("line_end", 0) - sym.get("line_start", 0) <= 2:
                    findings.append({
                        "type": "empty_class",
                        "severity": "medium",
                        "line": sym["line_start"],
                        "message": f"Empty class '{sym['name']}' has no implementation",
                        "file": "",
                        "details": {"class_name": sym["name"]},
                        "context": f"class {sym['name']}",
                        "confidence": 0.95,
                    })
        return findings

    @classmethod
    def _detect_nplus1_from_ast(cls, symbols: List[Dict[str, Any]], content: str) -> List[Dict[str, Any]]:
        """Detect N+1 queries using AST call graph."""
        findings: List[Dict[str, Any]] = []
        for sym in symbols:
            if sym.get("kind") == "function":
                calls = sym.get("calls", [])
                has_db_call = any(
                    "query" in str(c).lower() or "execute" in str(c).lower()
                    for c in calls
                )
                if has_db_call:
                    for call in calls:
                        if "query" in str(call).lower() or "execute" in str(call).lower():
                            findings.append({
                                "type": "nplus1_query",
                                "severity": "high",
                                "line": sym["line_start"],
                                "message": f"Potential N+1 query in function '{sym['name']}': database call inside loop",
                                "file": "",
                                "details": {"function_name": sym["name"], "call": str(call)},
                                "context": sym.get("signature", ""),
                                "confidence": 0.85,
                            })
        return findings

    @classmethod
    def _save_findings_to_db(cls, findings: Dict[str, List[Dict[str, Any]]], repo_id: str, db_path: str) -> None:
        """Save audit findings to database for repository-level tracking."""
        conn = None
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_findings (
                    id INTEGER PRIMARY KEY,
                    repo_id TEXT,
                    category TEXT,
                    severity TEXT,
                    file_path TEXT,
                    line_number INTEGER,
                    finding_type TEXT,
                    message TEXT,
                    details TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            for category, items in findings.items():
                for item in items:
                    conn.execute("""
                        INSERT INTO audit_findings
                        (repo_id, category, severity, file_path, line_number, finding_type, message, details, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        repo_id,
                        category,
                        item.get("severity", "medium"),
                        item.get("file", ""),
                        item.get("line", 0),
                        item.get("type", ""),
                        item.get("message", ""),
                        json.dumps(item.get("details", {})),
                        item.get("confidence", 0.5)
                    ))
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    @classmethod
    def _get_incremental_findings(cls, repo_id: str, db_path: str, since: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get findings from previous audits for incremental scanning."""
        findings: Dict[str, List[Dict[str, Any]]] = {}
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            query = "SELECT * FROM audit_findings WHERE repo_id = ?"
            params = [repo_id]
            if since:
                query += " AND created_at > ?"
                params.append(since)

            cursor = conn.execute(query, params)
            for row in cursor:
                category = row[3]
                if category not in findings:
                    findings[category] = []
                findings[category].append({
                    "severity": row[4],
                    "file": row[6],
                    "line": row[7],
                    "type": row[8],
                    "message": row[9],
                    "details": json.loads(row[10]) if row[10] else {},
                    "confidence": row[11]
                })
            conn.close()
        except Exception:
            pass
        return findings

    @classmethod
    def _detect_taint_flow(cls, symbols: List[Dict[str, Any]], edges: List[Dict], db_path: str) -> List[Dict[str, Any]]:
        """
        Detect data flow (taint tracking) from user input to dangerous sinks.
        Returns findings for SQL injection, command injection, path traversal.
        """
        findings: List[Dict[str, Any]] = []
        sources = {"request.args", "request.form", "request.json", "input", "sys.argv", "os.environ"}
        sinks = {"cursor.execute", "subprocess.run", "os.system", "open(", "eval(", "exec("}

        try:
            import sqlite3
            conn = sqlite3.connect(db_path)

            for sym in symbols:
                if sym.get("kind") != "function":
                    continue

                sym_name = sym.get("name", "")
                signature = sym.get("signature", "")

                for source in sources:
                    if source in signature or source in sym_name:
                        visited = set()
                        queue = [(sym_name, 1)]

                        while queue:
                            current, depth = queue.pop(0)
                            if current in visited or depth > 3:
                                continue
                            visited.add(current)

                            cursor = conn.execute("""
                                SELECT s2.name, e.relation FROM edges e
                                JOIN symbols s1 ON e.from_symbol_id = s1.id
                                JOIN symbols s2 ON e.to_symbol_id = s2.id
                                WHERE s1.name = ? AND e.relation = 'calls'
                            """, (current,))

                            for row in cursor:
                                target, relation = row
                                for sink in sinks:
                                    if sink in str(target):
                                        findings.append({
                                            "type": "taint_flow",
                                            "severity": "critical",
                                            "line": sym["line_start"],
                                            "message": f"Potential {sink[:-1]} injection: data flow from '{source}' to '{sink}'",
                                            "file": "",
                                            "details": {
                                                "source": source,
                                                "sink": sink,
                                                "path": [sym_name, current, target]
                                            },
                                            "context": signature,
                                            "confidence": 0.9,
                                        })
                                queue.append((target, depth + 1))
            conn.close()
        except Exception:
            pass

        return findings

    @classmethod
    def audit(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute code audit with specified parameters.

        Args:
            params: Audit configuration dictionary containing:
                - target_path: Path to file or directory to audit
                - scan_categories: Categories to scan (secrets, pii, misconfig, vulns, comments, structure, empty_code, nplus1)
                - include_git_history: Whether to scan git history
                - severity_threshold: Minimum severity level
                - generate_suggestions: Whether to generate recommendations
                - max_file_size_kb: Maximum file size to scan
                - files: Specific files to scan
                - output_format: Output format (json, csv, report)
                - db_path: Path to CodeAnalyzer database for AST integration
                - use_ast: Whether to use cached AST from CodeAnalyzer (default: True)

        Returns:
            Dictionary containing audit results and metadata
        """
        try:
            target_path = params.get("target_path", "")
            scan_categories = params.get("scan_categories", ["secrets", "pii", "misconfig", "vulns", "comments"])
            include_git_history = params.get("include_git_history", False)
            severity_threshold = params.get("severity_threshold", "medium")
            generate_suggestions = params.get("generate_suggestions", True)
            max_file_size_kb = params.get("max_file_size_kb", 1024)
            files = params.get("files")
            output_format = params.get("output_format", "json")
            db_path = params.get("db_path")
            use_ast = params.get("use_ast", True)
            repository_id = params.get("repository_id", "")
            since = params.get("since")

            target = Path(target_path).resolve()
            if not target.exists():
                return cls._error_response(f"Target path does not exist: {target_path}")

            max_bytes = max_file_size_kb * 1024
            severity_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            min_severity = severity_levels.get(severity_threshold, 1)

            aiignore_patterns = set()
            if params.get("use_aiignore", True):
                aiignore_patterns = cls._load_aiignore_patterns(str(target.parent if target.is_file() else target))

            findings: Dict[str, List[Dict[str, Any]]] = {
                "secrets": [],
                "pii": [],
                "misconfig": [],
                "vulnerabilities": [],
                "comment_tags": [],
                "nplus1": [],
                "empty_functions": [],
                "empty_classes": [],
                "unclosed_brackets": [],
                "unclosed_html_tags": [],
                "taint_flow": [],
            }
            errors: List[Dict[str, str]] = []
            scanned_files = 0
            total_findings = 0

            def _is_text_file(fpath: Path) -> bool:
                ext = fpath.suffix.lower()
                if ext in cls.SUPPORTED_EXTENSIONS:
                    return True
                try:
                    with open(fpath, "rb") as f:
                        head = f.read(1024)
                        return b"\x00" not in head
                except Exception:
                    return False

            def _extract_git_info(fpath: Path) -> Tuple[Optional[str], Optional[str]]:
                try:
                    import subprocess
                    result = subprocess.run(
                        ["git", "log", "-1", "--format=%an|%ai", "--", str(fpath)],
                        cwd=str(target.parent if target.is_file() else target),
                        capture_output=True, text=True, timeout=5,
                    )
                    if result.returncode == 0 and "|" in result.stdout:
                        parts = result.stdout.strip().split("|")
                        return parts[0], parts[1]
                except Exception:
                    pass
                return None, None

            def _scan_file(fpath: Path):
                nonlocal scanned_files, total_findings
                if not _is_text_file(fpath):
                    return
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    errors.append({
                        "file": str(fpath),
                        "error": f"Failed to read file: {str(e)}",
                    })
                    return

                if len(content) > max_bytes:
                    content = content[:max_bytes]
                scanned_files += 1

                lines = content.splitlines()
                author, last_modified = _extract_git_info(fpath)

                cached_symbols = None
                if use_ast and db_path:
                    cached_symbols = cls._get_cached_symbols(db_path, str(fpath))

                for category in scan_categories:
                    try:
                        if category == "secrets":
                            for match in cls._find_secrets(content):
                                if severity_levels.get(match["severity"], 0) >= min_severity:
                                    match["file"] = str(fpath)
                                    findings["secrets"].append(match)
                                    total_findings += 1
                        elif category == "pii":
                            for match in cls._find_pii(content):
                                if severity_levels.get(match["severity"], 0) >= min_severity:
                                    match["file"] = str(fpath)
                                    findings["pii"].append(match)
                                    total_findings += 1
                        elif category == "misconfig":
                            for match in cls._find_misconfig(content):
                                if severity_levels.get(match["severity"], 0) >= min_severity:
                                    match["file"] = str(fpath)
                                    findings["misconfig"].append(match)
                                    total_findings += 1
                        elif category == "vulns":
                            for match in cls._find_vulns(content):
                                if severity_levels.get(match["severity"], 0) >= min_severity:
                                    match["file"] = str(fpath)
                                    findings["vulnerabilities"].append(match)
                                    total_findings += 1
                        elif category == "comments":
                            tags = cls._find_comment_tags(content, str(fpath), author, last_modified)
                            for tag in tags:
                                findings["comment_tags"].append(asdict(tag))
                                total_findings += 1
                        elif category == "structure":
                            for match in cls._find_unclosed_brackets(content, str(fpath)):
                                if severity_levels.get(match["severity"], 0) >= min_severity:
                                    findings["unclosed_brackets"].append(match)
                                    total_findings += 1
                            for match in cls._find_unclosed_html_tags(content, str(fpath)):
                                if severity_levels.get(match["severity"], 0) >= min_severity:
                                    findings["unclosed_html_tags"].append(match)
                                    total_findings += 1
                        elif category == "empty_code":
                            if cached_symbols:
                                ast_findings = cls._analyze_empty_from_ast(cached_symbols)
                                for match in ast_findings:
                                    match["file"] = str(fpath)
                                    if severity_levels.get(match["severity"], 0) >= min_severity:
                                        findings["empty_functions"].append(match)
                                        findings["empty_classes"].append(match)
                                        total_findings += 1
                            else:
                                for match in cls._find_empty_functions(content, str(fpath)):
                                    if severity_levels.get(match["severity"], 0) >= min_severity:
                                        findings["empty_functions"].append(match)
                                        total_findings += 1
                                for match in cls._find_empty_classes(content, str(fpath)):
                                    if severity_levels.get(match["severity"], 0) >= min_severity:
                                        findings["empty_classes"].append(match)
                                        total_findings += 1
                        elif category == "nplus1":
                            if cached_symbols:
                                ast_nplus1 = cls._detect_nplus1_from_ast(cached_symbols, content)
                                for match in ast_nplus1:
                                    match["file"] = str(fpath)
                                    if severity_levels.get(match["severity"], 0) >= min_severity:
                                        findings["nplus1"].append(match)
                                        total_findings += 1
                            else:
                                for match in cls._find_nplus1_queries(content, str(fpath)):
                                    if severity_levels.get(match["severity"], 0) >= min_severity:
                                        findings["nplus1"].append(match)
                                        total_findings += 1
                    except Exception as e:
                        errors.append({
                            "file": str(fpath),
                            "error": f"Scan error in category {category}: {str(e)}",
                        })

            try:
                if files:
                    for f in files:
                        fp = Path(f)
                        if fp.exists() and fp.is_file():
                            if cls._should_exclude_file(str(fp), aiignore_patterns):
                                continue
                            _scan_file(fp)
                elif target.is_file():
                    if not cls._should_exclude_file(str(target), aiignore_patterns):
                        _scan_file(target)
                else:
                    for root, _dirs, fnames in os.walk(str(target)):
                        for fn in fnames:
                            fp = Path(root) / fn
                            if cls._should_exclude_file(str(fp), aiignore_patterns):
                                continue
                            _scan_file(fp)
            except Exception as e:
                return cls._error_response(f"Error scanning files: {str(e)}")

            if include_git_history:
                try:
                    git_secrets = cls._scan_git_history(target)
                    findings["secrets"].extend(git_secrets)
                    total_findings += len(git_secrets)
                except Exception as e:
                    errors.append({"stage": "git_history", "error": str(e)})

            if repository_id and db_path:
                try:
                    incremental_findings = cls._get_incremental_findings(repository_id, db_path, since)
                    for category, items in incremental_findings.items():
                        if category in findings:
                            findings[category].extend(items)
                            total_findings += len(items)
                except Exception as e:
                    errors.append({"stage": "incremental_scan", "error": str(e)})

            if use_ast and db_path and "taint_flow" in scan_categories:
                try:
                    all_symbols = []
                    for f in files or []:
                        fp = Path(f)
                        if fp.exists():
                            syms = cls._get_cached_symbols(db_path, str(fp))
                            if syms:
                                all_symbols.extend(syms)
                    if all_symbols:
                        taint_findings = cls._detect_taint_flow(all_symbols, [], db_path)
                        findings["taint_flow"].extend(taint_findings)
                        total_findings += len(taint_findings)
                except Exception as e:
                    errors.append({"stage": "taint_flow", "error": str(e)})

            summary = cls._build_summary(findings)
            recommendations = cls._generate_recommendations(findings) if generate_suggestions else {}

            if repository_id and db_path:
                try:
                    cls._save_findings_to_db(findings, repository_id, db_path)
                except Exception as e:
                    errors.append({"stage": "save_to_db", "error": str(e)})

            result = AuditResult(
                target=str(target),
                scan_categories=scan_categories,
                scanned_files=scanned_files,
                summary=summary,
                findings=findings,
                recommendations=recommendations,
                errors=errors,
            )

            data = result.__dict__

            return {
                "success": True,
                "status_code": 200,
                "message": f"Code audit complete: {total_findings} findings in {scanned_files} files",
                "data": data,
                "output_format": output_format,
            }

        except Exception as e:
            return cls._error_response(f"Audit failed: {str(e)}")

    @classmethod
    def _find_nplus1_queries(cls, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Detect N+1 query patterns in code.

        Common patterns:
        - for item in items: item.related.count()
        - for user in users: UserProfile.objects.get(user=user)
        - for (const user of users): await user.orders.count()
        - for (let i=0; i<items.length; i++): db.collection.find()
        """
        findings: List[Dict[str, Any]] = []
        lines = content.splitlines()

        loop_patterns = [
            r"for\s+\w+\s+in\s+",
            r"for\s+\w+\s+in\s+.+:",
            r"for\s*\(\s*(?:const|let)\s+\w+\s+of\s+",
            r"for\s*\(\s*let\s+\w+\s*=\s*\d+.*;\s*\w+\+\+",
        ]

        query_patterns = [
            r"\.\w+\.(count|get|all|filter)\s*\(",
            r"\.objects\.\w+\(",
            r"db\.\w+\.find",
            r"SELECT\s+.*\s+FROM\s+",
            r"await\s+\w+\.\w+\(",
            r"\.orders\.\w+\(\)",
            r"\.findMany\(\)",
            r"\.findUnique\(\)",
        ]

        for i, line in enumerate(lines, 1):
            loop_match = any(re.search(p, line) for p in loop_patterns)
            if loop_match:
                for j in range(i, min(i + 10, len(lines) + 1)):
                    inner_line = lines[j - 1] if j <= len(lines) else ""
                    query_match = any(re.search(p, inner_line) for p in query_patterns)
                    if query_match:
                        findings.append({
                            "type": "nplus1_query",
                            "severity": "high",
                            "line": i,
                            "column": 0,
                            "message": "Potential N+1 query detected: loop with database query inside",
                            "file": file_path,
                            "details": {
                                "loop_line": i,
                                "query_line": j,
                                "query_snippet": inner_line.strip()[:100],
                            },
                            "context": f"Line {i}: {line.strip()[:80]}",
                            "confidence": 0.85,
                        })
                        break

        return findings

    @classmethod
    def _find_empty_functions(cls, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detect empty function definitions (pass, raise NotImplementedError, or {})."""
        findings: List[Dict[str, Any]] = []
        lines = content.splitlines()

        func_pattern = r"def\s+(\w+)\s*\([^)]*\)\s*:"

        for i, line in enumerate(lines, 1):
            match = re.search(func_pattern, line)
            if match:
                func_name = match.group(1)
                is_empty = False

                if re.search(r":\s*\{\s*\}\s*$", line):
                    is_empty = True
                else:
                    for j in range(i + 1, min(i + 10, len(lines) + 1)):
                        if j > len(lines):
                            break
                        inner_line = lines[j - 1].strip()
                        if inner_line == "pass":
                            is_empty = True
                            break
                        if re.match(r"^raise\s+(NotImplementedError|NotImplemented)\b", inner_line):
                            is_empty = True
                            break
                        if re.match(r"^\s*{\s*}\s*$", inner_line):
                            is_empty = True
                            break
                        if inner_line and not inner_line.startswith(("#", '"""', "'''")):
                            break

                if is_empty:
                    findings.append({
                        "type": "empty_function",
                        "severity": "medium",
                        "line": i,
                        "column": 0,
                        "message": f"Empty function '{func_name}' has no implementation",
                        "file": file_path,
                        "details": {"function_name": func_name},
                        "context": line.strip()[:100],
                        "confidence": 0.95,
                    })

        return findings

    @classmethod
    def _find_empty_classes(cls, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detect empty class definitions."""
        findings: List[Dict[str, Any]] = []
        lines = content.splitlines()

        class_pattern = r"class\s+(\w+)(\([^)]*\))?\s*:"

        for i, line in enumerate(lines, 1):
            match = re.search(class_pattern, line)
            if match:
                class_name = match.group(1)
                is_empty = False

                if re.search(r":\s*\{\s*\}\s*$", line):
                    is_empty = True
                else:
                    for j in range(i + 1, min(i + 15, len(lines) + 1)):
                        if j > len(lines):
                            break
                        inner_line = lines[j - 1].strip()
                        if inner_line in ("pass",):
                            is_empty = True
                            break
                        if re.match(r"^\s*{\s*}\s*$", inner_line):
                            is_empty = True
                            break
                        if inner_line and not inner_line.startswith(("#", '"""', "'''", "class ", "def ")):
                            break

                if is_empty:
                    findings.append({
                        "type": "empty_class",
                        "severity": "medium",
                        "line": i,
                        "column": 0,
                        "message": f"Empty class '{class_name}' has no implementation",
                        "file": file_path,
                        "details": {"class_name": class_name},
                        "context": line.strip()[:100],
                        "confidence": 0.95,
                    })

        return findings

    @classmethod
    def _find_unclosed_brackets(cls, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detect unclosed brackets, braces, and parentheses."""
        findings: List[Dict[str, Any]] = []
        lines = content.splitlines()

        bracket_pairs = {"(": ")", "[": "]", "{": "}"}
        open_brackets = set(bracket_pairs.keys())

        for i, line in enumerate(lines, 1):
            stack: List[Tuple[str, int]] = []
            in_string = False
            string_char = None
            in_comment = False

            for j, char in enumerate(line):
                if char in ('"', "'") and (j == 0 or line[j-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None

                if not in_string and char == '#':
                    in_comment = True

                if not in_string and not in_comment:
                    if char in open_brackets:
                        stack.append((char, j))
                    elif char in bracket_pairs.values():
                        if stack:
                            last_bracket, _ = stack.pop()
                            if bracket_pairs[last_bracket] != char:
                                findings.append({
                                    "type": "mismatched_bracket",
                                    "severity": "high",
                                    "line": i,
                                    "column": j,
                                    "message": f"Mismatched brackets: expected {bracket_pairs[last_bracket]}, found {char}",
                                    "file": file_path,
                                    "details": {"expected": bracket_pairs[last_bracket], "found": char},
                                    "context": line.strip()[:100],
                                    "confidence": 0.9,
                                })
                        else:
                            findings.append({
                                "type": "unmatched_closing_bracket",
                                "severity": "high",
                                "line": i,
                                "column": j,
                                "message": f"Unmatched closing bracket: {char}",
                                "file": file_path,
                                "details": {"bracket": char},
                                "context": line.strip()[:100],
                                "confidence": 0.85,
                            })

            for open_bracket, col in stack:
                findings.append({
                    "type": "unclosed_bracket",
                    "severity": "high",
                    "line": i,
                    "column": col,
                    "message": f"Unclosed bracket: '{open_bracket}'",
                    "file": file_path,
                    "details": {"bracket": open_bracket},
                    "context": line.strip()[:100],
                    "confidence": 0.9,
                })

        return findings

    @classmethod
    def _find_unclosed_html_tags(cls, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detect unclosed HTML/XML tags."""
        findings: List[Dict[str, Any]] = []

        void_elements = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

        tag_pattern = r"<(\/?)(\w+)([^>]*)>"

        open_tags: List[Tuple[str, int]] = []

        for i, line in enumerate(content.splitlines(), 1):
            for match in re.finditer(tag_pattern, line):
                is_closing = match.group(1) == "/"
                tag_name = match.group(2).lower()

                if is_closing:
                    if open_tags and open_tags[-1][0] == tag_name:
                        open_tags.pop()
                    elif tag_name not in void_elements:
                        findings.append({
                            "type": "unexpected_closing_tag",
                            "severity": "medium",
                            "line": i,
                            "column": match.start(),
                            "message": f"Unexpected closing tag: </{tag_name}>",
                            "file": file_path,
                            "details": {"tag": tag_name},
                            "context": line.strip()[:100],
                            "confidence": 0.8,
                        })
                else:
                    if tag_name not in void_elements:
                        open_tags.append((tag_name, match.start()))

        for tag_name, col in open_tags:
            findings.append({
                "type": "unclosed_html_tag",
                "severity": "medium",
                "line": 0,
                "column": col,
                "message": f"Unclosed HTML tag: <{tag_name}>",
                "file": file_path,
                "details": {"tag": tag_name},
                "context": "",
                "confidence": 0.85,
            })

        return findings

    @classmethod
    def _find_comment_tags(
        cls,
        content: str,
        file_path: str,
        author: Optional[str],
        last_modified: Optional[str]
    ) -> List[CommentTag]:
        """
        Find all comment tags in source code using robust regex matching.
        """
        tags: List[CommentTag] = []
        seen: Set[Tuple[int, str]] = set()
        lines = content.splitlines()

        for rule in TAG_PATTERNS:
            tag = rule["tag"]
            pattern = rule["pattern"]
            priority = rule["priority"]

            try:
                for m in re.finditer(pattern, content):
                    line_num = content[:m.start()].count("\n") + 1

                    if line_num <= 0 or line_num > len(lines):
                        continue

                    key = (line_num, tag)
                    if key in seen:
                        continue
                    seen.add(key)

                    col = m.start() - content.rfind("\n", 0, m.start())

                    line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                    context_start = max(0, m.start() - 50)
                    context_end = min(len(content), m.end() + 100)
                    context = content[context_start:context_end].replace("\n", " ").strip()

                    message_match = re.search(r'[:;]\s*(.+)$', line_content)
                    message = message_match.group(1).strip()[:100] if message_match else line_content.strip()[:100]

                    comment_type = cls._detect_comment_type(content, m.start())
                    confidence = cls._calculate_confidence(content, m, line_content)

                    tags.append(CommentTag(
                        tag=tag,
                        priority=priority,
                        line=line_num,
                        column=col,
                        message=message,
                        file=file_path,
                        author=author,
                        last_modified=last_modified,
                        context=context,
                        confidence=confidence,
                        comment_type=comment_type,
                    ))
            except re.error as e:
                logger.warning(f"Regex error for pattern '{pattern}': {e}")
                continue

        return tags

    @classmethod
    def _detect_comment_type(cls, content: str, pos: int) -> str:
        """Detect the type of comment at the given position."""
        before = content[:pos]
        line_start = before.rfind("\n") + 1
        line = content[line_start:content.find("\n", pos)]

        if line.strip().startswith("#"):
            return "line"
        elif line.strip().startswith("//"):
            return "line"
        elif line.strip().startswith("--"):
            return "line"
        elif "/*" in before and "*/" not in before[pos:]:
            return "block"
        elif '"""' in before or "'''" in before:
            return "docstring"
        return "line"

    @classmethod
    def _calculate_confidence(cls, content: str, match: re.Match, line_content: str) -> float:
        """Calculate confidence score for a tag detection."""
        confidence = 1.0

        if not line_content.strip().startswith(("//", "#", "--", "/*", "*", "* ", "###")):
            confidence -= 0.2

        if re.search(r'["\'].*' + match.group() + r'["\']', line_content):
            confidence -= 0.3

        if line_content.strip().startswith("import ") or line_content.strip().startswith("def ") or line_content.strip().startswith("class "):
            confidence -= 0.2

        return max(0.1, min(1.0, confidence))

    @classmethod
    def _build_summary(cls, findings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """Build summary statistics from findings."""
        summary: Dict[str, int] = {}
        for cat, matches in findings.items():
            for m in matches:
                sev = m.get("severity", m.get("priority", "unknown"))
                summary[sev] = summary.get(sev, 0) + 1
        return summary

    @classmethod
    def _error_response(cls, message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "success": False,
            "status_code": 400,
            "message": message,
            "data": None,
        }

    @classmethod
    def _calculate_entropy(cls, s: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not s:
            return 0.0
        freq = {}
        for c in s:
            freq[c] = freq.get(c, 0) + 1
        length = len(s)
        entropy = 0.0
        for f in freq.values():
            p = f / length
            entropy -= p * math.log2(p)
        return entropy

    @classmethod
    def _variable_name_risk_score(cls, var_name: str) -> float:
        """Calculate risk score based on variable name patterns."""
        risk_indicators = {
            "password": 0.9,
            "passwd": 0.9,
            "secret": 0.85,
            "api_key": 0.8,
            "apikey": 0.8,
            "token": 0.7,
            "credential": 0.85,
            "private_key": 0.9,
            "access_key": 0.75,
            "auth": 0.6,
        }
        var_lower = var_name.lower()
        for indicator, score in risk_indicators.items():
            if indicator in var_lower:
                return score
        return 0.1

    @classmethod
    def _context_analysis(cls, line: str, var_name: str, value: str) -> Tuple[bool, str]:
        """Analyze context to reduce false positives."""
        line_lower = line.lower()
        placeholder_patterns = [
            "your-", "example", "placeholder", "dummy", "fake",
            "test", "sample", "xxx", "change_me", "replace_me"
        ]
        for pattern in placeholder_patterns:
            if pattern in value.lower():
                return False, "placeholder_value"
        if "os.environ" in line or "getenv" in line or "process.env" in line:
            return False, "environment_variable"
        if "const " not in line and "let " not in line and "var " not in line:
            if "=" in line and not line.strip().startswith("#"):
                return True, "direct_assignment"
        return True, "potential_secret"

    @classmethod
    def _find_secrets(cls, content: str) -> List[Dict[str, Any]]:
        """Find potential secrets and credentials in code using multi-layer detection."""
        patterns = [
            {"name": "aws_access_key", "regex": r"AKIA[0-9A-Z]{16}", "severity": "critical"},
            {"name": "aws_secret_key", "regex": r"(?i)(aws_secret_access_key|secret_access_key)\s*[=:]\s*['\"]([A-Za-z0-9/+=]{40})['\"]", "severity": "critical"},
            {"name": "github_token", "regex": r"ghp_[A-Za-z0-9]{36}", "severity": "critical"},
            {"name": "private_key", "regex": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "severity": "critical"},
        ]
        matches = []
        lines = content.splitlines()
        for rule in patterns:
            for m in re.finditer(rule["regex"], content):
                line_num = content[:m.start()].count("\n") + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                value = m.group()
                entropy = cls._calculate_entropy(value)
                confidence = min(1.0, entropy / 4.0 + 0.5)
                is_placeholder, reason = cls._context_analysis(line_content, rule["name"], value)
                if "placeholder" in reason:
                    confidence *= 0.3
                matches.append({
                    "type": rule["name"],
                    "severity": rule["severity"],
                    "line": line_num,
                    "value": value[:20] + "...",
                    "context": line_content.strip()[:100],
                    "confidence": round(confidence, 2),
                    "entropy": round(entropy, 2),
                })
        var_name_pattern = r"(?P<var_name>(?:password|passwd|secret|api_key|apikey|token|credential|private_key|access_key)\s*[=:])\s*['\"](?P<value>[^\'\"]{8,})['\"]"
        for m in re.finditer(var_name_pattern, content, re.IGNORECASE):
            line_num = content[:m.start()].count("\n") + 1
            line_content = lines[line_num - 1] if line_num <= len(lines) else ""
            var_name = m.group("var_name")
            value = m.group("value")
            risk_score = cls._variable_name_risk_score(var_name)
            entropy = cls._calculate_entropy(value)
            is_real, reason = cls._context_analysis(line_content, var_name, value)
            confidence = risk_score * (entropy / 4.0 + 0.5) if is_real else risk_score * 0.3
            matches.append({
                "type": "high_risk_variable",
                "severity": "high" if risk_score > 0.7 else "medium",
                "line": line_num,
                "variable_name": var_name.strip(),
                "value": value[:20] + "...",
                "context": line_content.strip()[:100],
                "confidence": round(confidence, 2),
                "risk_score": round(risk_score, 2),
                "entropy": round(entropy, 2),
            })
        return matches

    @classmethod
    def _find_pii(cls, content: str) -> List[Dict[str, Any]]:
        """Find potential PII in code."""
        patterns = [
            {"name": "email", "regex": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "severity": "medium"},
            {"name": "ssn", "regex": r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "severity": "high"},
        ]
        matches = []
        for rule in patterns:
            for m in re.finditer(rule["regex"], content):
                line_num = content[:m.start()].count("\n") + 1
                matches.append({
                    "type": rule["name"],
                    "severity": rule["severity"],
                    "line": line_num,
                    "value": m.group()[:20] + "...",
                })
        return matches

    @classmethod
    def _find_misconfig(cls, content: str) -> List[Dict[str, Any]]:
        """Find configuration issues in code."""
        patterns = [
            {"name": "debug_enabled", "regex": r"(?i)(debug\s*[=:]\s*true|DEBUG\s*=\s*True)", "severity": "medium"},
            {"name": "cors_wildcard", "regex": r"(?i)cors.*['\"]\*['\"]", "severity": "high"},
        ]
        matches = []
        for rule in patterns:
            for m in re.finditer(rule["regex"], content):
                line_num = content[:m.start()].count("\n") + 1
                matches.append({
                    "type": rule["name"],
                    "severity": rule["severity"],
                    "line": line_num,
                })
        return matches

    @classmethod
    def _find_vulns(cls, content: str) -> List[Dict[str, Any]]:
        """Find potential vulnerabilities in code."""
        patterns = [
            {"name": "sql_injection", "regex": r"(?i)(execute|query)\s*\(\s*['\"].*\{.*\}.*['\"]", "severity": "critical"},
            {"name": "eval_usage", "regex": r"(?i)\beval\s*\(", "severity": "high"},
            {"name": "pickle_load", "regex": r"(?i)pickle\.(load|loads)\s*\(", "severity": "high"},
        ]
        matches = []
        for rule in patterns:
            for m in re.finditer(rule["regex"], content):
                line_num = content[:m.start()].count("\n") + 1
                matches.append({
                    "type": rule["name"],
                    "severity": rule["severity"],
                    "line": line_num,
                })
        return matches

    @classmethod
    def _scan_git_history(cls, target: Path) -> List[Dict[str, Any]]:
        """Scan git history for sensitive information."""
        import subprocess
        results: List[Dict[str, Any]] = []
        try:
            git_root = target if target.is_dir() else target.parent
            for _ in range(20):
                if (git_root / ".git").exists():
                    break
                if git_root == git_root.parent:
                    return results
                git_root = git_root.parent
            if not (git_root / ".git").exists():
                return results

            log = subprocess.run(
                ["git", "log", "--all", "--full-history", "-p", "--since=2020-01-01", "--max-count=50"],
                cwd=str(git_root), capture_output=True, text=True, timeout=60,
            )
            if log.returncode == 0 and log.stdout.strip():
                for rule in [p for p in TAG_PATTERNS if p["priority"] in ("critical", "high")]:
                    for m in re.finditer(rule["pattern"], log.stdout):
                        if len(results) >= 50:
                            return results
                        line = log.stdout[:m.start()].count("\n") + 1
                        results.append({
                            "type": rule["tag"],
                            "severity": rule["priority"],
                            "line": line,
                            "source": "git_history",
                        })
        except Exception:
            pass
        return results

    @classmethod
    def _generate_recommendations(cls, findings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Generate recommendations based on findings."""
        gitignore_entries: Set[str] = set()
        secrets_to_rotate: Set[str] = set()
        files_to_remove: Set[str] = set()

        for cat, matches in findings.items():
            for m in matches:
                fp = m.get("file", "")
                if m.get("severity") in ("critical", "high"):
                    if cat == "secrets" and m.get("type") in ("password_field", "connection_string"):
                        gitignore_entries.add(os.path.basename(fp))
                    if m.get("type") in ("aws_access_key", "aws_secret_key", "github_token"):
                        secrets_to_rotate.add(m.get("value", "")[:20])
                if fp and m.get("severity") == "critical":
                    files_to_remove.add(os.path.basename(fp))

        return {
            "gitignore_entries": sorted(gitignore_entries),
            "secrets_to_rotate": list(secrets_to_rotate),
            "files_to_remove": sorted(files_to_remove),
        }

    @classmethod
    def export_results(cls, data: Dict[str, Any], format: str = "json", output_path: Optional[str] = None) -> str:
        """
        Export audit results in specified format.

        Args:
            data: Audit results dictionary
            format: Output format (json, csv, report)
            output_path: Optional path to write output

        Returns:
            Formatted output string
        """
        try:
            if format == "json":
                result = json.dumps(data, indent=2, default=str)
            elif format == "csv":
                result = cls._export_csv(data)
            else:
                result = cls._export_report(data)

            if output_path:
                Path(output_path).write_text(result, encoding="utf-8")
            return result
        except Exception as e:
            return f"Export failed: {str(e)}"

    @classmethod
    def _export_csv(cls, data: Dict[str, Any]) -> str:
        """Export results as CSV."""
        lines = ["file,tag,priority,line,message,author,last_modified,comment_type,confidence"]
        for tag in data.get("findings", {}).get("comment_tags", []):
            lines.append(f'"{tag["file"]}","{tag["tag"]}","{tag["priority"]}",{tag["line"]},"{tag["message"]}","{tag.get("author", "")}","{tag.get("last_modified", "")}","{tag.get("comment_type", "")}",{tag["confidence"]}')
        return "\n".join(lines)

    @classmethod
    def _export_report(cls, data: Dict[str, Any]) -> str:
        """Export results as human-readable report."""
        lines = [
            "=" * 60,
            "CODE AUDIT REPORT",
            "=" * 60,
            f"Target: {data.get('target', 'N/A')}",
            f"Scanned Files: {data.get('scanned_files', 0)}",
            "",
            "SUMMARY:",
        ]
        for sev, count in data.get("summary", {}).items():
            lines.append(f"  {sev.upper()}: {count}")
        lines.append("")
        lines.append("COMMENT TAGS DETECTED:")
        for tag in data.get("findings", {}).get("comment_tags", []):
            lines.append(f"  [{tag['priority']}] {tag['file']}:{tag['line']} - {tag['tag']}: {tag['message'][:50]}")
        lines.append("=" * 60)
        return "\n".join(lines)
