"""
Code Analysis Tool for indexing and graph building using Tree-sitter.

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.Analyzer
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from __future__ import annotations

import os
import json
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, timezone

from src.core.utils.language import detect_language
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger("CodeCortex.CodeAnalysis.CodeAnalyzer")

def _log_structured(event: str, **kwargs):
    import json
    from datetime import datetime
    entry = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    logger.info(json.dumps(entry))

@dataclass
class Symbol:
    name: str
    kind: str
    file_path: str
    line_start: int
    line_end: int
    signature: str = ""
    docstring: str = ""
    parent_symbol: Optional[str] = None
    calls: List[str] = field(default_factory=list)
    referenced_by: List[str] = field(default_factory=list)

@dataclass
class Edge:
    from_symbol: str
    to_symbol: str
    relation: str

class CodeAnalyzer:
    SUPPORTED_LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.rb': 'ruby',
        '.php': 'php',
        '.kt': 'kotlin',
        '.swift': 'swift',
        '.zig': 'zig',
        '.lua': 'lua',
        '.ex': 'elixir',
        '.exs': 'elixir',
        '.clj': 'clojure',
        '.cs': 'csharp',
        '.vue': 'vue',
        '.svelte': 'svelte',
    }

    LANGUAGE_GRAMMAR_MAP = {
        'python': 'python',
        'javascript': 'javascript',
        'typescript': 'typescript',
        'java': 'java',
        'go': 'go',
        'rust': 'rust',
        'cpp': 'cpp',
        'c': 'c',
        'ruby': 'ruby',
        'php': 'php',
        'kotlin': 'kotlin',
        'swift': 'swift',
        'zig': 'zig',
        'lua': 'lua',
        'elixir': 'elixir',
        'clojure': 'clojure',
        'csharp': 'csharp',
        'vue': 'vue',
        'svelte': 'svelte',
    }

    def __init__(self, db: Any):
        self.db = db
        self._tree_sitter_available = self._check_tree_sitter()
        self._ensure_tables()

    def _check_tree_sitter(self) -> bool:
        try:
            import tree_sitter
            return True
        except ImportError:
            logger.warning("Tree-sitter not available, falling back to simple parsing")
            return False

    def _ensure_tables(self):
        conn = self.db.conn
        conn.execute(
            """
                CREATE TABLE IF NOT EXISTS analyzer_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    hash TEXT,
                    last_modified TEXT,
                    language TEXT,
                    size_bytes INTEGER
                )
            """
        )
        conn.execute(
            """
                CREATE TABLE IF NOT EXISTS analyzer_symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    name TEXT,
                    kind TEXT,
                    line_start INTEGER,
                    line_end INTEGER,
                    signature TEXT,
                    docstring TEXT,
                    parent_symbol_id INTEGER,
                    calls TEXT,
                    FOREIGN KEY(file_id) REFERENCES analyzer_files(id)
                )
            """
        )
        conn.execute(
            """
                CREATE TABLE IF NOT EXISTS analyzer_edges (
                    from_symbol_id INTEGER,
                    to_symbol_id INTEGER,
                    relation TEXT,
                    FOREIGN KEY(from_symbol_id) REFERENCES analyzer_symbols(id),
                    FOREIGN KEY(to_symbol_id) REFERENCES analyzer_symbols(id)
                )
            """
        )
        self.db.conn.commit()

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def _detect_language(self, file_path: str) -> str:
        return detect_language(file_path)

    def _parse_with_tree_sitter(self, content: str, language: str) -> Tuple[List[Symbol], List[Edge]]:
        symbols = []
        edges = []

        if not self._tree_sitter_available:
            return self._parse_simple(content, language)

        try:
            import tree_sitter
            from tree_sitter import Language, Parser

            grammar_name = self.LANGUAGE_GRAMMAR_MAP.get(language)
            if not grammar_name:
                return self._parse_simple(content, language)

            try:
                Language('build/language-py', 'python')
            except Exception:
                return self._parse_simple(content, language)

            parser = Parser()
            parser.language = Language('build/language-py', 'python')

            tree = parser.parse(content.encode())
            self._extract_symbols_from_tree(tree, content, symbols, edges, "")

        except Exception as e:
            logger.debug(f"Tree-sitter parsing failed: {e}, falling back to simple parsing")
            return self._parse_simple(content, language)

        return symbols, edges

    def _extract_symbols_from_tree(self, node, content: str, symbols: List[Symbol], edges: List[Edge], parent: str):
        pass

    def _parse_simple(self, content: str, language: str) -> Tuple[List[Symbol], List[Edge]]:
        symbols = []
        edges = []
        lines = content.split('\n')

        if language == 'python':
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('def '):
                    name = stripped.split('(')[0].replace('def ', '').strip()
                    sig = stripped
                    docstring = ""
                    for j in range(i, min(i + 20, len(lines) + 1)):
                        if j <= len(lines):
                            doc_line = lines[j - 1].strip()
                            if doc_line.startswith('"""') or doc_line.startswith("'''"):
                                docstring = doc_line
                                break
                    symbols.append(Symbol(
                        name=name,
                        kind='function',
                        file_path='',
                        line_start=i,
                        line_end=i,
                        signature=sig,
                        docstring=docstring,
                        parent_symbol=parent
                    ))
                elif stripped.startswith('class '):
                    name = stripped.split(':')[0].replace('class ', '').strip()
                    symbols.append(Symbol(
                        name=name,
                        kind='class',
                        file_path='',
                        line_start=i,
                        line_end=i,
                        parent_symbol=parent
                    ))

        return symbols, edges

    def analyze_file(self, file_path: str, content: str, repo_id: str) -> Dict[str, Any]:
        language = self._detect_language(file_path)
        file_hash = self._compute_hash(content)
        now = datetime.now(timezone.utc).isoformat()

        conn = self.db.conn
        cursor = conn.execute(
            "SELECT id, hash FROM analyzer_files WHERE path = ?", (file_path,)
        )
        row = cursor.fetchone()

        created = False
        if row:
            file_id, old_hash = row[0], row[1]
            if old_hash == file_hash:
                return {"file_id": file_id, "symbols_count": 0, "edges_count": 0, "status": "unchanged"}
            conn.execute("DELETE FROM analyzer_symbols WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM analyzer_edges WHERE from_symbol_id IN (SELECT id FROM analyzer_symbols WHERE file_id = ?)", (file_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO analyzer_files (path, hash, last_modified, language, size_bytes) VALUES (?, ?, ?, ?, ?)",
                (file_path, file_hash, now, language, len(content))
            )
            file_id = cursor.lastrowid
            created = True

        symbols, edges = self._parse_with_tree_sitter(content, language)

        symbol_ids = {}
        for sym in symbols:
            sym.file_path = file_path
            cursor = conn.execute(
                "INSERT INTO analyzer_symbols (file_id, name, kind, line_start, line_end, signature, docstring, parent_symbol_id, calls) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (file_id, sym.name, sym.kind, sym.line_start, sym.line_end, sym.signature, sym.docstring, None, json.dumps(sym.calls))
            )
            symbol_ids[sym.name] = cursor.lastrowid

        for edge in edges:
            from_id = symbol_ids.get(edge.from_symbol)
            to_id = symbol_ids.get(edge.to_symbol)
            if from_id and to_id:
                conn.execute(
                    "INSERT INTO analyzer_edges (from_symbol_id, to_symbol_id, relation) VALUES (?, ?, ?)",
                    (from_id, to_id, edge.relation)
                )

        self.db.conn.commit()

        return {
            "file_id": file_id,
            "symbols_count": len(symbols),
            "edges_count": len(edges),
            "status": "created" if created else "updated"
        }

    def get_symbols(self, file_path: str) -> List[Dict]:
        conn = self.db.conn
        cursor = conn.execute(
            "SELECT id, name, kind, line_start, line_end, signature, docstring FROM analyzer_symbols WHERE file_id = (SELECT id FROM analyzer_files WHERE path = ?)",
            (file_path,)
        )
        symbols = []
        for row in cursor:
            symbols.append({
                "id": row[0],
                "name": row[1],
                "kind": row[2],
                "line_start": row[3],
                "line_end": row[4],
                "signature": row[5] or "",
                "docstring": row[6] or ""
            })
        return symbols

    def get_edges(self, symbol_name: str) -> List[Dict]:
        conn = self.db.conn
        cursor = conn.execute(
            """
            SELECT s1.name as from_symbol, s2.name as to_symbol, e.relation
            FROM analyzer_edges e
            JOIN analyzer_symbols s1 ON e.from_symbol_id = s1.id
            JOIN analyzer_symbols s2 ON e.to_symbol_id = s2.id
            WHERE s1.name = ?
            """, (symbol_name,))
        edges = []
        for row in cursor:
            edges.append({
                "from": row[0],
                "to": row[1],
                "relation": row[2]
            })
        return edges

    def get_call_graph(self, symbol_name: str, follow_depth: int = 2) -> Dict[str, Any]:
        visited = set()
        result = {"nodes": [], "edges": []}

        def traverse(current: str, depth: int):
            if current in visited or depth > follow_depth:
                return
            visited.add(current)

            cursor = self.db.conn.execute(
                """
                SELECT s2.name, e.relation FROM analyzer_edges e
                JOIN analyzer_symbols s1 ON e.from_symbol_id = s1.id
                JOIN analyzer_symbols s2 ON e.to_symbol_id = s2.id
                WHERE s1.name = ?
                """, (current,))

            for row in cursor:
                target, relation = row[0], row[1]
                result["edges"].append({"from": current, "to": target, "relation": relation})
                result["nodes"].append(target)
                traverse(target, depth + 1)

        traverse(symbol_name, 1)
        return result

    def build_directory_tree(self, target_path: str, max_depth: int = 3, cursor: Optional[str] = None) -> Dict[str, Any]:
        target = Path(target_path)
        if not target.exists():
            return {"children": [], "message": "Path does not exist"}

        cursor_obj = self.db.conn.execute(
            "SELECT d.relative_path || '/' || f.name, f.classification, s.name, s.symbol_type, s.line_start FROM analyzer_files f LEFT JOIN analyzer_symbols s ON f.id = s.file_id LEFT JOIN directories d ON f.directory_id = d.id"
        )

        file_data = {}
        for row in cursor_obj:
            path, lang, sym_name, sym_kind, line = row[0], row[1], row[2], row[3], row[4]
            if path not in file_data:
                file_data[path] = {"functions": [], "classes": [], "language": lang or ""}
            if sym_kind == 'function':
                file_data[path]["functions"].append(sym_name)
            elif sym_kind == 'class':
                file_data[path]["classes"].append(sym_name)

        children = self._build_tree_recursive(target, target, max_depth, file_data)

        return {
            "mode": "overview",
            "target": str(target),
            "type": "directory" if target.is_dir() else "file",
            "children": children,
            "next_cursor": None,
            "has_more": False
        }

    def _build_tree_recursive(self, root: Path, current: Path, max_depth: int, file_data: Dict) -> List[Dict]:
        if current.is_file():
            path_str = str(current)
            data = file_data.get(path_str, {"functions": [], "classes": [], "language": "unknown"})
            lang = data["language"]
            return [{
                "name": current.name,
                "type": "file",
                "functions": data["functions"],
                "classes": data["classes"],
                "lines": 0,
                "summary": f"{lang} file"
            }]

        children = []
        try:
            items = sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for item in items[:100]:
                if item.name.startswith('.') and item.name not in ('.', '..'):
                    continue
                child = self._build_tree_recursive(root, item, max_depth - 1, file_data)
                if isinstance(child, list):
                    children.extend(child)
                else:
                    children.append(child)
        except PermissionError:
            pass

        return children

    def analyze_symbol(self, symbol_name: str, follow_depth: int = 2) -> Dict[str, Any]:
        conn = self.db.conn
        cursor = conn.execute(
            """
            SELECT s.name, s.symbol_type, d.relative_path || '/' || f.name, s.line_start, s.line_end, s.signature, s.docstring
            FROM analyzer_symbols s
            JOIN analyzer_files f ON s.file_id = f.id
            JOIN directories d ON f.directory_id = d.id
            WHERE s.name = ?
            """, (symbol_name,))

        row = cursor.fetchone()
        if not row:
            return {"error": f"Symbol '{symbol_name}' not found. Symbol lookup is case-sensitive exact-match."}

        symbol_info = {
            "symbol": row[0],
            "kind": row[1],
            "file": row[2],
            "line_start": row[3],
            "line_end": row[4],
            "signature": row[5] or "",
            "docstring": row[6] or ""
        }

        cursor = conn.execute(
            """
            SELECT s2.name FROM analyzer_edges e
            JOIN analyzer_symbols s1 ON e.from_symbol_id = s1.id
            JOIN analyzer_symbols s2 ON e.to_symbol_id = s2.id
            WHERE s1.name = ? AND e.relation = 'calls'
            """, (symbol_name,))
        calls = [r[0] for r in cursor.fetchall()]
        symbol_info["calls"] = calls

        cursor = conn.execute(
            """
            SELECT s1.name FROM analyzer_edges e
            JOIN analyzer_symbols s2 ON e.to_symbol_id = s2.id
            JOIN analyzer_symbols s1 ON e.from_symbol_id = s1.id
            WHERE s2.name = ? AND e.relation = 'calls'
            """, (symbol_name,))
        called_by = [r[0] for r in cursor.fetchall()]
        symbol_info["called_by"] = called_by

        return {
            "mode": "symbol_focus",
            "symbol": symbol_name,
            **symbol_info,
            "complexity": {"cyclomatic": 0, "cognitive": 0}
        }
