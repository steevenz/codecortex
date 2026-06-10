"""
Database Analyzer — extracts SQL queries, ORM calls, and schema information
from source code for runtime intelligence.

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.Db_analyzer
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


class DatabaseAnalyzer:
    """Extract database queries, ORM calls, and schema from code."""

    SQL_PATTERNS = [
        re.compile(r"""(?:execute|exec|query|raw)\s*\(\s*["'](SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s""", re.I),
        re.compile(r"""session\.(query|execute|add|commit|rollback|flush)\s*\(""", re.I),
        re.compile(r"""cursor\.(execute|fetchone|fetchall|fetchmany)\s*\(""", re.I),
        re.compile(r"""db\.(query|execute|fetch|select|insert|update|delete)\s*\(""", re.I),
        re.compile(r"""\.filter\s*\([^)]*==\s*\w"""),
        re.compile(r"""\.all\(\s*\)"""),
        re.compile(r"""\.first\(\s*\)"""),
        re.compile(r"""\.join\s*\([^)]*"""),
    ]

    TABLE_PATTERNS = [
        re.compile(r"""CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)""", re.I),
        re.compile(r"""__tablename__\s*=\s*["'](\w+)["']"""),
        re.compile(r"""@Table\s*\(\s*["'](\w+)["']"""),
        re.compile(r"""table\s*\(\s*["'](\w+)["']"""),
    ]

    def analyze(self, root_path: str) -> Dict[str, Any]:
        root = Path(root_path)
        queries: List[Dict] = []
        tables: List[Dict] = []

        for fp in root.rglob("*"):
            if fp.suffix not in (".py", ".js", ".ts", ".sql", ".prisma"):
                continue
            if not fp.is_file():
                continue
            if any(p.startswith(".") or p in ("node_modules", "venv", "__pycache__") for p in fp.relative_to(root).parts):
                continue

            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Extract queries
            for pattern in self.SQL_PATTERNS:
                for m in pattern.finditer(content):
                    line_num = content[:m.start()].count("\n") + 1
                    snippet = content[max(0, m.start() - 30):m.end() + 50]
                    queries.append({
                        "file": str(fp.relative_to(root)),
                        "line": line_num,
                        "pattern": m.group(0)[:120],
                        "snippet": snippet.strip()[:200],
                    })

            # Extract tables
            for pattern in self.TABLE_PATTERNS:
                for m in pattern.finditer(content):
                    tables.append({
                        "name": m.group(1),
                        "file": str(fp.relative_to(root)),
                        "line": content[:m.start()].count("\n") + 1,
                    })

        return {
            "total_queries": len(queries),
            "total_tables": len(tables),
            "tables": tables[:30],
            "queries": queries[:50],
            "by_type": {
                "sql_raw": sum(1 for q in queries if "SELECT" in q["pattern"] or "INSERT" in q["pattern"]),
                "orm": sum(1 for q in queries if "session" in q["pattern"] or "query" in q["pattern"]),
            },
        }
