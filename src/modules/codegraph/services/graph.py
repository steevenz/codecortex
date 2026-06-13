"""
Class Graph – Unified Architectural Intelligence Service.
Handles both low-level graph construction and high-level analytical modeling.

:project: CodeCortex
:package: Modules.Codegraph.Services.Graph
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

import asyncio
import json
import logging
import os
import importlib
import networkx as nx
from datetime import datetime
from typing import List, Dict, Optional, Any, Literal, Union
from pathlib import Path

from src.core.database import DatabaseManager
from src.core.graph import GraphManager
from src.core.logging import get_logger
from src.core.logging.event_logger import log_event
from src.core import env_flag

# Mixins & Infrastructure
from src.modules.codegraph.services.mixins.analysis import ArchitecturalAnalysisMixin
from src.modules.codegraph.services.mixins.discovery import ArchitecturalDiscoveryMixin
from src.modules.codegraph.services.mixins.reporter import ArchitecturalReporterMixin
from src.modules.codegraph.services.mixins.security import ArchitecturalSecurityMixin
from src.modules.codegraph.services.mixins.search import CodeSearchMixin
from src.modules.codegraph.graph_builders.persistence.writer import GraphWriter
from src.modules.codegraph.graph_builders.office import OfficeWorker

# AST Resolution Helpers
from src.modules.codegraph.services.resolution.calls import build_function_call_groups
from src.modules.codegraph.services.resolution.inheritance import build_inheritance_and_csharp_files
from src.modules.codeindex.parsers.parsers.tree_sitter import TreeSitterParser
from src.modules.codeindex.parsers.parsers.languages.python import pre_scan_python

logger = get_logger("CodeCortex.Domain.CodeGraph")

class Graph(
    ArchitecturalAnalysisMixin,
    ArchitecturalDiscoveryMixin,
    ArchitecturalReporterMixin,
    ArchitecturalSecurityMixin,
    CodeSearchMixin
):
    """
    Unified Architectural Intelligence Service.
    Consolidates Graph Construction (legacy CodeGraph) and High-Level Analysis (legacy Graphify).
    """
    def __init__(self, db: DatabaseManager, code_index_service=None):
        self.db = db
        self.code_index_service = code_index_service
        self._graph_manager = None
        self._graph_writer = None
        self.office_worker = OfficeWorker()

    @property
    def graph_manager(self) -> GraphManager:
        if self._graph_manager is None:
            self._graph_manager = self.db.graph_manager
        return self._graph_manager

    @property
    def graph_writer(self) -> GraphWriter:
        if self._graph_writer is None:
            self._graph_writer = GraphWriter(self.graph_manager)
        return self._graph_writer

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: str = "internal"):
        log_event(level, event_code, context, request_id=request_id, logger=getattr(self, 'logger', None))

    async def run_in_thread(self, sync_func, *args, **kwargs):
        """
        Execute a synchronous function in a thread pool.

        Provides a reusable wrapper around asyncio.to_thread for offloading
        blocking operations from the event loop.

        Args:
            sync_func: Synchronous function to execute.
            args: Positional arguments to pass to the function.
            kwargs: Keyword arguments to pass to the function.

        Returns:
            Result of the synchronous function.
        """
        return await asyncio.to_thread(sync_func, *args, **kwargs)

    # -------------------------------------------------------------------------
    # Graph Construction (Persistence)
    # -------------------------------------------------------------------------

    async def map_relationships(self, repo_id: str):
        """DEPRECATED: Use write_repository_graph() via the indexing pipeline."""
        self._log_event("WARN", "RELATIONSHIP_MAPPING_DEPRECATED", {
            "repository_id": repo_id, "use": "write_repository_graph"
        })
        def _get_info():
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            row = cursor.fetchone()
            if not row:
                return None, None
            repo_root = Path(row['root_path'])
            cursor = self.db.conn.execute(
                "SELECT f.id, f.name, d.relative_path AS dir_path "
                "FROM files f JOIN directories d ON d.id = f.directory_id "
                "WHERE f.repository_id = ?",
                (repo_id,),
            )
            files = cursor.fetchall()
            return repo_root, files

        repo_root, files = await asyncio.to_thread(_get_info)
        if not repo_root:
            self._log_event("ERROR", "REPO_NOT_FOUND", {"repository_id": repo_id}, "internal")
            return

        file_paths: List[Path] = []
        for f in files:
            dir_path = (f['dir_path'] or "").replace("\\", "/")
            rel = f"{dir_path}/{f['name']}" if dir_path else f['name']
            fp = repo_root / rel
            if await asyncio.to_thread(fp.exists):
                file_paths.append(fp)
        return await self.build_repository_graph(repo_id, repo_root, file_paths)

    async def write_repository_graph(
        self,
        repo_id: str,
        repo_path: Path,
        parsed_files: List[Dict[str, Any]],
        imports_map: Dict[str, List[str]],
        request_id: str = "internal"
    ) -> None:
        """
        Write parsed AST data to the graph backend (Kùzu/Neo4j/FalkorDB).
        Uses batch writes for CALLS and INHERITS edges to avoid per-row round-trips.
        """
        self._log_event("INFO", "GRAPH_WRITE_STARTED", {"repository_id": repo_id}, request_id)
        backend_type = self.graph_manager.get_backend_type()
        if backend_type in {"none", "noop"}:
            self._log_event("INFO", "GRAPH_WRITE_SKIPPED", {
                "repository_id": repo_id, "backend": backend_type
            })
            return

        gw = self.graph_writer
        now = datetime.now().isoformat()
        await asyncio.to_thread(gw.merge_repo, str(repo_path), repo_path.name, now, repo_id)

        def _write_nodes():
            # Upsert File/Function/Class nodes
            for fd in parsed_files:
                fpath = fd.get("path", "")
                if not fpath:
                    continue
                rel_path = str(fpath).replace("\\", "/")
                if Path(fpath).is_absolute():
                    try:
                        rel_path = str(Path(fpath).relative_to(repo_path)).replace("\\", "/")
                    except Exception:
                        rel_path = Path(fpath).name
                gw.merge_file(fpath, Path(fpath).name, rel_path, str(repo_path), fd.get("is_dependency", False))
                for fn in fd.get("functions", []):
                    fn_copy = dict(fn)
                    fn_copy["path"] = fpath
                    gw.merge_fn(fn_copy)
                    gw.link_contains(
                        "File", "path", fpath,
                        "Function", "uid", f"fn:{fpath}:{fn['name']}:{fn['line_number']}",
                    )
                for cls in fd.get("classes", []):
                    cls_copy = dict(cls)
                    cls_copy["path"] = fpath
                    gw.merge_cls(cls_copy)
                    gw.link_contains(
                        "File", "path", fpath,
                        "Class", "uid", f"cls:{fpath}:{cls['name']}:{cls['line_number']}",
                    )

        await asyncio.to_thread(_write_nodes)

        def _write_batches():
            # ---- Batch CALLS edges ----
            fn_fn, fn_cls, cls_fn, cls_cls, file_fn, file_cls = build_function_call_groups(
                parsed_files, imports_map
            )

            def _make_call_item(c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                called_path = c.get("called_file_path")
                caller_name = c.get("caller_name")
                called_name = c.get("called_name")
                if not called_path or not called_name:
                    return None
                return {
                    "caller_name": caller_name or "",
                    "caller_path": c.get("caller_file_path", ""),
                    "callee_name": called_name,
                    "callee_path": called_path,
                    "line_number": c.get("line_number", 0),
                    "full_call_name": c.get("full_call_name", ""),
                }

            def _do_batch(group: List[Dict], caller_label: str, callee_label: str) -> None:
                items = [item for c in group if (item := _make_call_item(c)) is not None]
                if items:
                    try:
                        gw.write_calls_batch(caller_label, callee_label, items)
                    except Exception as e:
                        self._log_event("WARN", "CALLS_BATCH_FAILED", {
                            "caller": caller_label, "callee": callee_label, "error": str(e)
                        })

            _do_batch(fn_fn,   "Function", "Function")
            _do_batch(fn_cls,  "Function", "Class")
            _do_batch(cls_fn,  "Class",    "Function")
            _do_batch(cls_cls, "Class",    "Class")
            _do_batch(file_fn, "File",     "Function")
            _do_batch(file_cls,"File",     "Class")

            return fn_fn, fn_cls, cls_fn, cls_cls, file_fn, file_cls

        fn_fn, fn_cls, cls_fn, cls_cls, file_fn, file_cls = await asyncio.to_thread(_write_batches)

        def _write_inheritance():
            # ---- Batch INHERITS edges ----
            inherits, _csharp_files = build_inheritance_and_csharp_files(parsed_files, imports_map)

            # Build lookup for exact class line numbers so INHERITS UIDs match stored Class nodes
            class_line_lookup: Dict[str, int] = {}
            for fd in parsed_files:
                fpath = str(fd.get("path", ""))
                for cls in fd.get("classes", []):
                    key = f"{fpath}:{cls.get('name', '')}"
                    class_line_lookup[key] = cls.get("line_number", 0)

            inherit_items: List[Dict[str, Any]] = []
            for i in inherits:
                child_path = i["path"]
                parent_path = i.get("resolved_parent_file_path", child_path) or child_path
                child_line = class_line_lookup.get(f"{child_path}:{i['child_name']}", 0)
                parent_line = class_line_lookup.get(f"{parent_path}:{i['parent_name']}", 0)
                child = f"cls:{child_path}:{i['child_name']}:{child_line}"
                parent = f"cls:{parent_path}:{i['parent_name']}:{parent_line}"
                inherit_items.append({
                    "child_name": i["child_name"],
                    "child_path": child_path,
                    "parent_name": i["parent_name"],
                    "parent_path": parent_path,
                })
                gw.link_inherits(child, parent)

            if inherit_items:
                try:
                    self._log_event("INFO", "GRAPH_WRITE_COMPLETED", {"repository_id": repo_id}, request_id)
                except Exception as e:
                    self._log_event("ERROR", "GRAPH_WRITE_FAILED", {"repository_id": repo_id, "error": str(e)}, request_id)
            return inherit_items

        inherit_items = await asyncio.to_thread(_write_inheritance)

        self._log_event("INFO", "GRAPH_WRITE_COMPLETED", {
            "repository_id": repo_id,
            "files": len(parsed_files),
            "calls_fn_fn": len(fn_fn),
            "calls_total": len(fn_fn) + len(fn_cls) + len(cls_fn) + len(cls_cls) + len(file_fn) + len(file_cls),
            "inherits": len(inherit_items),
        }, request_id)

    async def build_repository_graph(
        self,
        repo_id: str,
        repo_path: Path,
        files: List[Path],
    ) -> Dict[str, Any]:
        """
        Full graph construction pipeline: parse files → resolve calls/inheritance → persist to graph backend.
        """
        self._log_event("INFO", "GRAPH_BUILD_STARTED", {
            "repository_id": repo_id, "files_count": len(files)
        })
        parsed_files: List[Dict[str, Any]] = []
        language_files: Dict[str, List[Path]] = {}

        def _scan_files():
            for fpath in files:
                if not fpath.exists():
                    continue
                ext = fpath.suffix.lower()
                lang = self._detect_language(fpath, ext)
                language_files.setdefault(lang, []).append(fpath)
            return language_files

        language_files = await asyncio.to_thread(_scan_files)

        # Pre-scan Python imports for cross-file call resolution
        imports_map: Dict[str, List[str]] = {}
        if "python" in language_files:
            if self.code_index_service:
                imports_map = await self.code_index_service.pre_scan_repository(repo_id)
            else:
                def _do_prescan():
                    try:
                        py_parser = TreeSitterParser("python")
                        return pre_scan_python(language_files["python"], py_parser)
                    except Exception as e:
                        logger.warning("Standalone pre-scan failed: %s", e)
                        return {}
                imports_map = await asyncio.to_thread(_do_prescan)
                logger.info("Standalone pre-scan: %d symbols mapped", len(imports_map))

        for lang, file_list in language_files.items():
            async def _parse_lang_files():
                try:
                    parser = TreeSitterParser(lang)
                    for fpath in file_list:
                        is_notebook = fpath.suffix == ".ipynb"
                        # Parsing is CPU intensive, offload to thread
                        parsed_data = await asyncio.to_thread(parser.parse, fpath, is_notebook=is_notebook, index_source=True)
                        if "error" not in parsed_data:
                            parsed_files.append(parsed_data)
                        else:
                            logger.warning("Parse error %s: %s", fpath, parsed_data.get("error"))
                except Exception as e:
                    logger.error("Failed to parse %s files: %s", lang, e)
            await _parse_lang_files()

        await self.write_repository_graph(repo_id, repo_path, parsed_files, imports_map)

        stats = {
            "files_parsed": len(parsed_files),
            "total_functions": sum(len(f.get("functions", [])) for f in parsed_files),
            "total_classes": sum(len(f.get("classes", [])) for f in parsed_files),
            "languages": list(language_files.keys()),
        }
        self._log_event("INFO", "GRAPH_BUILD_COMPLETED", {"repository_id": repo_id, "stats": stats})
        return stats

    def _detect_language(self, fpath: Path, ext: str) -> str:
        lang_map = {
            ".py": "python", ".ipynb": "python",
            ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "tsx",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
            ".c": "c", ".h": "c",
            ".java": "java",
            ".rb": "ruby",
            ".cs": "c_sharp",
            ".php": "php",
            ".kt": "kotlin", ".kts": "kotlin",
            ".scala": "scala",
            ".swift": "swift",
            ".hs": "haskell",
            ".dart": "dart",
            ".pl": "perl", ".pm": "perl",
            ".ex": "elixir", ".exs": "elixir",
            ".css": "css", ".scss": "css", ".sass": "css", ".less": "css",
        }
        return lang_map.get(ext, "python")

    # -------------------------------------------------------------------------
    # Architectural Intelligence (Analysis)
    # -------------------------------------------------------------------------

    async def analyze_architecture(self, repo_id: str) -> Dict[str, Any]:
        """Run the full suite of graph-based analyses using native Mixins."""
        self._log_event("INFO", "ARCHITECTURAL_ANALYSIS_STARTED", {"repository_id": repo_id})

        # Build Graph from DB (Offloaded to thread)
        G = await self._build_graph_from_db(repo_id)

        # Heavy computations offloaded to threads
        god_nodes = await asyncio.to_thread(self.find_god_nodes, G)
        communities = await asyncio.to_thread(self.cluster_communities, G)
        node_to_comm = {node: cid for cid, nodes in communities.items() for node in nodes}

        # Analyze connections
        def _calc_coupling():
            coupling = []
            for u, v, data in G.edges(data=True):
                score = self.calculate_surprise_score(G, u, v, node_to_comm)
                if score > 0.4:
                    coupling.append({
                        "source": u,
                        "target": v,
                        "score": score,
                        "relation": data.get("relation_type", "CALLS")
                    })
            return coupling

        coupling = await asyncio.to_thread(_calc_coupling)

        security = self._audit_security_hygiene(repo_id)
        questions = await asyncio.to_thread(self.suggest_architectural_questions, G, god_nodes)

        analysis_result = {
            "god_nodes": god_nodes,
            "communities_count": len(communities),
            "surprising_connections": sorted(coupling, key=lambda x: x["score"], reverse=True)[:10],
            "security_hygiene": security,
            "suggested_questions": questions
        }

        self._log_event("INFO", "ARCHITECTURAL_ANALYSIS_COMPLETED", {"repository_id": repo_id})
        return analysis_result

    async def _build_graph_from_db(self, repo_id: str) -> nx.DiGraph:
        """Helper to reconstruct a NetworkX graph from the SQLite store."""
        def _build():
            G = nx.DiGraph()
            # Add symbols as nodes
            nodes = self.db.conn.execute(
                "SELECT id, name, symbol_type FROM symbols WHERE repository_id = ?",
                (repo_id,)
            ).fetchall()
            for n in nodes:
                G.add_node(n["id"], label=n["name"], type=n["symbol_type"])

            # Add edges
            edges = self.db.conn.execute(
                "SELECT source_id, target_id, weight, relation_type FROM edges WHERE repository_id = ?",
                (repo_id,)
            ).fetchall()
            for e in edges:
                G.add_edge(e["source_id"], e["target_id"], weight=e["weight"], relation_type=e["relation_type"])
            return G

        return await asyncio.to_thread(_build)

    async def build_comprehensive_report(self, repo_id: str, request_id: str = "internal") -> Dict[str, Any]:
        self._log_event("INFO", "REPORT_GENERATION_STARTED", {"repository_id": repo_id}, request_id)
        def _get_repo_info():
            return self.db.conn.execute(
                "SELECT id, name, root_path, sync_at FROM repositories WHERE id = ?",
                (repo_id,),
            ).fetchone()

        repo_row = await asyncio.to_thread(_get_repo_info)
        if not repo_row:
            return {"error": "repository_not_found", "repository_id": repo_id}

        repo_root = Path(repo_row["root_path"])

        # Fetch stats in parallel threads
        tree_stats, ast_stats, graph_stats = await asyncio.gather(
            self._repo_tree_stats(repo_id),
            self._ast_stats(repo_id),
            self._dependency_graph_stats(repo_id)
        )

        def _get_dot():
            return self._dependency_graph_dot(repo_id, limit_edges=200)

        graph_stats["visualization"] = {
            "format": "graphviz_dot",
            "dot": await asyncio.to_thread(_get_dot),
        }

        # Build Graph once for all analyses
        G = await self._build_graph_from_db(repo_id)

        # Offload remaining heavy analysis to threads
        god_nodes = await asyncio.to_thread(self.find_god_nodes, G)
        communities = await asyncio.to_thread(self.cluster_communities, G)
        node_to_comm = {str(node): cid for cid, nodes in communities.items() for node in nodes}

        def _calc_coupling():
            coupling = []
            for u, v, data in G.edges(data=True):
                score = self.calculate_surprise_score(G, str(u), str(v), node_to_comm)
                if score > 0.4:
                    coupling.append({
                        "source": u,
                        "target": v,
                        "score": score,
                        "relation": data.get("relation_type", "CALLS")
                    })
            return coupling

        coupling = await asyncio.to_thread(_calc_coupling)

        # Fetch other findings in parallel where possible
        entrypoints, lint, security, code_quality, module_analysis, hotspots, temporal_coupling = await asyncio.gather(
            self._entrypoints(repo_id),
            self._lint_findings(repo_id),
            asyncio.to_thread(self._audit_security_hygiene, repo_id),
            self._code_quality_metrics(repo_id),
            asyncio.to_thread(self.analyze_module_dependencies, repo_id),
            asyncio.to_thread(self.analyze_hotspots, repo_id),
            asyncio.to_thread(self.analyze_temporal_coupling, repo_id)
        )

        def _do_manual_checks():
            tests = self._test_and_coverage_findings(repo_root)
            docs = self._documentation_completeness(repo_root, ast_stats)
            health = self._repository_health(repo_root, tree_stats, tests, docs)
            return tests, docs, health

        tests, docs, health = await asyncio.to_thread(_do_manual_checks)

        questions = await asyncio.to_thread(self.suggest_architectural_questions, G, god_nodes, communities)

        report_data = {
            "repo_name": repo_row["name"],
            "total_files": tree_stats.get("files_count", 0),
            "god_nodes": god_nodes,
            "communities": communities,
            "hotspots": hotspots,
            "temporal_coupling": temporal_coupling,
            "module_analysis": module_analysis,
            "questions": questions
        }

        markdown = await asyncio.to_thread(self.generate_markdown_report, report_data)

        return {
            "repository": {
                "id": repo_row["id"],
                "name": repo_row["name"],
                "root_path": str(repo_root),
                "sync_at": repo_row["sync_at"],
            },
            "directory_tree": tree_stats,
            "ast_analysis": ast_stats,
            "dependency_graph": graph_stats,
            "god_nodes": god_nodes,
            "hotspots": hotspots,
            "temporal_coupling": temporal_coupling,
            "module_analysis": module_analysis,
            "questions": questions,
            "communities_count": len(communities),
            "code_coupling": {"surprising_connections": sorted(coupling, key=lambda x: x["score"], reverse=True)[:10]},
            "code_flow": {"entrypoints": entrypoints},
            "lint": lint,
            "testing": tests,
            "code_quality": code_quality,
            "documentation": docs,
            "security": security,
            "repository_health": health,
            "summary": markdown
        }

    async def _repo_tree_stats(self, repo_id: str) -> Dict[str, Any]:
        def _get():
            dirs = self.db.conn.execute(
                "SELECT COUNT(1) AS c FROM directories WHERE repository_id = ?",
                (repo_id,),
            ).fetchone()["c"]
            files = self.db.conn.execute(
                "SELECT COUNT(1) AS c FROM files WHERE repository_id = ?",
                (repo_id,),
            ).fetchone()["c"]
            by_class = self.db.conn.execute(
                "SELECT classification, COUNT(1) AS c FROM files WHERE repository_id = ? GROUP BY classification",
                (repo_id,),
            ).fetchall()
            return {
                "directories_count": dirs,
                "files_count": files,
                "files_by_classification": {r["classification"]: r["c"] for r in by_class},
            }
        return await asyncio.to_thread(_get)

    async def _ast_stats(self, repo_id: str) -> Dict[str, Any]:
        def _get():
            by_type = self.db.conn.execute(
                "SELECT symbol_type, COUNT(1) AS c FROM symbols WHERE repository_id = ? GROUP BY symbol_type",
                (repo_id,),
            ).fetchall()
            total = sum(r["c"] for r in by_type)
            documented = self.db.conn.execute(
                "SELECT COUNT(1) AS c FROM symbols WHERE repository_id = ? AND docstring IS NOT NULL AND LENGTH(TRIM(docstring)) > 0",
                (repo_id,),
            ).fetchone()["c"]
            return {
                "symbols_total": total,
                "symbols_by_type": {r["symbol_type"]: r["c"] for r in by_type},
                "docstring_coverage": (documented / total) if total else 0.0,
            }
        return await asyncio.to_thread(_get)

    async def _dependency_graph_stats(self, repo_id: str) -> Dict[str, Any]:
        def _get():
            by_rel = self.db.conn.execute(
                "SELECT relation_type, COUNT(1) AS c FROM edges WHERE repository_id = ? GROUP BY relation_type",
                (repo_id,),
            ).fetchall()
            top_calls = self.db.conn.execute(
                """
                SELECT e.source_id, e.target_id, e.weight
                FROM edges e
                WHERE e.repository_id = ? AND e.relation_type = 'CALLS'
                ORDER BY e.weight DESC
                LIMIT 25
                """,
                (repo_id,),
            ).fetchall()
            resolved: List[Dict[str, Any]] = []
            if top_calls:
                ids: List[str] = []
                for r in top_calls:
                    ids.append(r["source_id"])
                    ids.append(r["target_id"])
                placeholders = ",".join(["?"] * len(set(ids)))
                sym_rows = self.db.conn.execute(
                    f"SELECT id, name, file_id, symbol_type FROM symbols WHERE id IN ({placeholders})",
                    tuple(set(ids)),
                ).fetchall()
                id_to_sym = {r["id"]: dict(r) for r in sym_rows}
                for r in top_calls:
                    src = id_to_sym.get(r["source_id"])
                    tgt = id_to_sym.get(r["target_id"])
                    resolved.append({"source": src, "target": tgt, "weight": r["weight"]})
            return {
                "edges_by_relation": {r["relation_type"]: r["c"] for r in by_rel},
                "top_calls": resolved,
            }
        return await asyncio.to_thread(_get)

    def _dependency_graph_dot(self, repo_id: str, limit_edges: int = 200) -> str:
        rows = self.db.conn.execute(
            """
            SELECT s1.name AS source_name, s2.name AS target_name
            FROM edges e
            JOIN symbols s1 ON e.source_id = s1.id
            JOIN symbols s2 ON e.target_id = s2.id
            WHERE e.repository_id = ? AND e.relation_type = 'CALLS'
            LIMIT ?
            """,
            (repo_id, int(limit_edges)),
        ).fetchall()
        lines = ["digraph G {"]
        for r in rows:
            src = (r["source_name"] or "").replace('"', '\\"')
            tgt = (r["target_name"] or "").replace('"', '\\"')
            if src and tgt:
                lines.append(f'  "{src}" -> "{tgt}";')
        lines.append("}")
        return "\n".join(lines)

    async def _entrypoints(self, repo_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        def _get():
            rows = self.db.conn.execute(
                """
                SELECT s.id, s.name, s.symbol_type
                FROM symbols s
                LEFT JOIN edges e
                  ON e.repository_id = s.repository_id
                 AND e.relation_type = 'CALLS'
                 AND e.target_id = s.id
                WHERE s.repository_id = ? AND s.symbol_type IN ('function', 'method') AND e.id IS NULL
                LIMIT ?
                """,
                (repo_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        return await asyncio.to_thread(_get)

    async def _lint_findings(self, repo_id: str) -> Dict[str, Any]:
        def _get():
            rows = self.db.conn.execute(
                "SELECT insight_type, metadata, created_at FROM insights WHERE repository_id = ? AND category = 'lint' ORDER BY created_at DESC LIMIT 200",
                (repo_id,),
            ).fetchall()
            items: List[Dict[str, Any]] = []
            for r in rows:
                meta_raw = r["metadata"]
                try:
                    meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                except Exception:
                    meta = {"raw": meta_raw}
                items.append({"type": r["insight_type"], "metadata": meta, "created_at": r["created_at"]})
            return {"findings": items, "count": len(items)}
        return await asyncio.to_thread(_get)

    def _test_and_coverage_findings(self, repo_root: Path) -> Dict[str, Any]:
        candidates = {
            "pytest": ["pytest.ini", "conftest.py"],
            "unittest": ["tests", "test"],
            "jest": ["package.json", "jest.config.js", "jest.config.ts"],
            "vitest": ["vitest.config.ts", "vitest.config.js"],
        }
        detected: List[str] = []
        for k, hints in candidates.items():
            for h in hints:
                if (repo_root / h).exists():
                    detected.append(k)
                    break

        test_files = 0
        for base in ["tests", "test"]:
            p = repo_root / base
            if p.exists() and p.is_dir():
                for root, dirs, files in os.walk(p):
                    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}]
                    for fn in files:
                        if fn.startswith("test_") or fn.endswith("_test.py") or fn.endswith(".spec.ts") or fn.endswith(".test.ts"):
                            test_files += 1

        coverage_artifacts: List[str] = []
        for cand in ["coverage.xml", ".coverage", "htmlcov", "coverage", "lcov.info", "coverage/lcov.info"]:
            if (repo_root / cand).exists():
                coverage_artifacts.append(cand)

        return {
            "detected_frameworks": sorted(list(set(detected))),
            "test_files_count": test_files,
            "coverage_artifacts": coverage_artifacts,
        }

    def _documentation_completeness(self, repo_root: Path, ast_stats: Dict[str, Any]) -> Dict[str, Any]:
        required = ["README.md", "SECURITY.md", "LICENSE"]
        present = {p: (repo_root / p).exists() for p in required}
        docs_dir = (repo_root / "docs").exists()
        return {
            "required_files": present,
            "docs_dir_present": docs_dir,
            "docstring_coverage": ast_stats.get("docstring_coverage", 0.0),
        }

    async def _code_quality_metrics(self, repo_id: str) -> Dict[str, Any]:
        def _get():
            rows = self.db.conn.execute(
                """
                SELECT id, name, start_line, end_line
                FROM symbols
                WHERE repository_id = ? AND symbol_type IN ('function', 'method') AND start_line IS NOT NULL AND end_line IS NOT NULL
                """,
                (repo_id,),
            ).fetchall()
            lengths: List[int] = []
            for r in rows:
                try:
                    ln = int(r["end_line"]) - int(r["start_line"]) + 1
                except Exception:
                    continue
                if ln > 0:
                    lengths.append(ln)
            lengths.sort(reverse=True)
            p95 = lengths[max(0, int(len(lengths) * 0.95) - 1)] if lengths else 0
            return {
                "functions_count": len(lengths),
                "max_function_lines": lengths[0] if lengths else 0,
                "p95_function_lines": p95,
            }
        return await asyncio.to_thread(_get)

    def _repository_health(self, repo_root: Path, tree_stats: Dict[str, Any], tests: Dict[str, Any], docs: Dict[str, Any]) -> Dict[str, Any]:
        has_git = (repo_root / ".git").exists()
        has_ci = (repo_root / ".github" / "workflows").exists()
        return {
            "has_git_directory": has_git,
            "has_ci_workflows": has_ci,
            "files_by_classification": tree_stats.get("files_by_classification", {}),
            "test_files_count": tests.get("test_files_count", 0),
            "docs_dir_present": docs.get("docs_dir_present", False),
        }
