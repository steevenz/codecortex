"""
Class Analyze – Single Responsibility: AST-aware code analysis
with Tree-Sitter extraction + knowledge graph.
Depends on: db (DatabaseManager), fs_service (Filesystem), graph_service.

:project: CodeCortex
:package: Modules.Codeanalysis.Services.Analyze
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from __future__ import annotations

import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from src.core.database import DatabaseManager
from src.core.logging import get_logger
from src.core.utils.language import detect_language
from src.modules.filesystem.core.service import Filesystem
from src.modules.codeanalysis.core.dtos import (
    AnalyzedSymbol, AnalyzedEdge, AnalyzeRequest, AnalyzeResult,
)

logger = get_logger("CodeCortex.CodeAnalysis.AnalyzeService")

class Analyze:
    """
    AST-aware code analysis with Tree-Sitter symbol extraction and graph building.
    Uses DI: all dependencies injected via constructor.
    """

    def __init__(self, db, fs_service: Filesystem):
        self._db = db
        self._fs = fs_service
        self._tree_sitter_available = self._check_tree_sitter()

    def _get_conn(self):
        if hasattr(self._db, 'connection'):
            return self._db.connection
        elif hasattr(self._db, 'conn'):
            return self._db.conn
        return self._db

    def _check_tree_sitter(self) -> bool:
        try:
            import tree_sitter
            return True
        except ImportError:
            logger.warning("Tree-sitter not available, using regex fallback")
            return False

    def _detect_language(self, file_path: str) -> str:
        return detect_language(file_path)

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResult:
        # Batch analysis: multiple targets
        if request.targets and len(request.targets) > 1:
            return self._analyze_batch(request)

        target = Path(request.target)
        if not target.exists():
            raise FileNotFoundError(f"Target path does not exist: {request.target}")

        if request.mode == "symbol_focus" and request.focus:
            return self._analyze_symbol(request.focus, request.follow_depth)
        if request.mode == "overview":
            return self._build_directory_tree(target, request.max_depth, request.cursor)

        symbols = self._get_symbols_from_db(str(target))
        return AnalyzeResult(
            mode="detailed",
            target=str(target),
            symbols=symbols,
            count=len(symbols),
        )

    def _analyze_batch(self, request: AnalyzeRequest) -> AnalyzeResult:
        """Analyze multiple targets in parallel (10/10 AI coder impact feature)."""
        targets = request.targets or [request.target]
        all_symbols: List[AnalyzedSymbol] = []
        all_edges: List[AnalyzedEdge] = []
        errors: List[Dict[str, str]] = []

        def analyze_single(target_path: str) -> Tuple[str, Optional[List[AnalyzedSymbol]], Optional[str]]:
            try:
                target = Path(target_path)
                if not target.exists():
                    return target_path, None, f"Path does not exist: {target_path}"
                symbols = self._get_symbols_from_db(str(target))
                return target_path, symbols, None
            except Exception as e:
                return target_path, None, str(e)

        if request.parallel and len(targets) > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=request.max_workers) as executor:
                futures = {executor.submit(analyze_single, t): t for t in targets}
                for future in as_completed(futures):
                    target_path, symbols, error = future.result()
                    if error:
                        errors.append({"target": target_path, "error": error})
                    elif symbols:
                        all_symbols.extend(symbols)
        else:
            # Sequential processing
            for target_path in targets:
                target_path, symbols, error = analyze_single(target_path)
                if error:
                    errors.append({"target": target_path, "error": error})
                elif symbols:
                    all_symbols.extend(symbols)

        # Build edges for all symbols (cross-target call graph)
        if request.follow_depth > 0:
            conn = self._get_conn()
            for symbol in all_symbols[:50]:  # Limit to prevent explosion
                edges = self._build_call_graph(symbol.name, request.follow_depth, conn)
                all_edges.extend(edges)

        result = AnalyzeResult(
            mode="batch_detailed",
            target=f"batch:{len(targets)}_targets",
            symbols=all_symbols,
            edges=all_edges,
            count=len(all_symbols),
        )
        # Store errors in a way they can be accessed
        if errors:
            logger.warning(f"Batch analysis errors: {errors}")
        return result

    def _analyze_symbol(self, symbol_name: str, follow_depth: int = 2) -> AnalyzeResult:
        conn = self._get_conn()
        cursor = conn.execute("""
            SELECT s.name, s.symbol_type, f.relative_path, s.start_line, s.end_line, s.signature, s.docstring
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            WHERE s.name = ?
        """, (symbol_name,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Symbol '{symbol_name}' not found")

        symbol = AnalyzedSymbol(
            name=row[0], kind=row[1], file_path=row[2],
            line_start=row[3], line_end=row[4],
            signature=row[5] or "", docstring=row[6] or "",
        )
        cursor.execute("""
            SELECT s2.name FROM edges e
            JOIN symbols s1 ON e.from_symbol_id = s1.id
            JOIN symbols s2 ON e.to_symbol_id = s2.id
            WHERE s1.name = ? AND e.relation = 'calls'
        """, (symbol_name,))
        symbol.calls = [r[0] for r in cursor.fetchall()]

        cursor.execute("""
            SELECT s1.name FROM edges e
            JOIN symbols s2 ON e.to_symbol_id = s2.id
            JOIN symbols s1 ON e.from_symbol_id = s1.id
            WHERE s2.name = ? AND e.relation = 'calls'
        """, (symbol_name,))
        symbol.referenced_by = [r[0] for r in cursor.fetchall()]

        edges = self._build_call_graph(symbol_name, follow_depth, conn)
        return AnalyzeResult(
            mode="symbol_focus", target=symbol_name,
            symbols=[symbol], edges=edges, count=1,
        )

    def _build_call_graph(self, symbol_name: str, depth: int, conn) -> List[AnalyzedEdge]:
        visited = set()
        edges: List[AnalyzedEdge] = []

        def _traverse(current: str, remaining: int):
            if current in visited or remaining < 0:
                return
            visited.add(current)
            cursor = conn.execute("""
                SELECT s2.name FROM edges e
                JOIN symbols s1 ON e.from_symbol_id = s1.id
                JOIN symbols s2 ON e.to_symbol_id = s2.id
                WHERE s1.name = ? AND e.relation = 'calls'
            """, (current,))
            for (target_name,) in cursor:
                edges.append(AnalyzedEdge(from_symbol=current, to_symbol=target_name, relation='calls'))
                _traverse(target_name, remaining - 1)

        _traverse(symbol_name, depth)
        return edges

    def _get_symbols_from_db(self, file_path: str) -> List[AnalyzedSymbol]:
        conn = self._get_conn()
        file_name = Path(file_path).name
        cursor = conn.execute(
            "SELECT s.id, s.name, s.symbol_type, f.relative_path, s.start_line, s.end_line, s.signature, s.docstring FROM symbols s JOIN files f ON s.file_id = f.id WHERE f.name = ?",
            (file_name,)
        )
        symbols = []
        for row in cursor:
            symbols.append(AnalyzedSymbol(
                name=row[1], kind=row[2], file_path=row[3],
                line_start=row[4], line_end=row[5],
                signature=row[6] or "", docstring=row[7] or "",
            ))
        return symbols

    def _build_directory_tree(self, root: Path, max_depth: int, cursor: Optional[str]) -> AnalyzeResult:
        children = self._walk_tree(root, root, max_depth, cursor)
        return AnalyzeResult(
            mode="overview", target=str(root),
            tree=children, has_more=False,
        )

    def _walk_tree(self, root: Path, current: Path, depth: int, cursor: Optional[str]) -> List[Dict[str, Any]]:
        if depth <= 0 or not current.exists():
            return []

        if current.is_file():
            return [{"name": current.name, "type": "file", "language": self._detect_language(str(current))}]

        items = []
        try:
            for child in sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                if child.name.startswith('.'):
                    continue
                items.extend(self._walk_tree(root, child, depth - 1, cursor))
        except PermissionError:
            pass
        return [{"name": current.name, "type": "directory", "children": items}] if items else []
