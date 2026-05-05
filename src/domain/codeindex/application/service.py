"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeIndex
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class CodeIndexService – Single Responsibility: Manage AST semantic indexing and symbol nesting.
 */
"""

import concurrent.futures
import asyncio
import ast
import importlib
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

from src.core.database import DatabaseManager
from src.core.logging_config import get_logger
from src.core import env_flag
from src.domain.codeindex.infrastructure.strategies.base import BaseStrategy, RawSymbol
from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
from src.domain.codeindex.infrastructure.parsers.languages.python import pre_scan_python
from src.domain.codeindex.core.converters import parsed_data_to_raw_symbols
from src.domain.codeindex.infrastructure.parsers.frameworks import nextjs as nextjs_fw
from src.domain.codeindex.infrastructure.parsers.frameworks import flutter as flutter_fw
from src.domain.codeindex.infrastructure.parsers.frameworks import laravel as laravel_fw
from src.domain.coderepository.infrastructure.detector import RepositoryFrameworkDetector

logger = get_logger("CodeCortex.Domain.CodeIndex")

class CodeIndexService:
    """
    Orchestrates AST parsing and semantic storage with production stability.
    Supports 20+ languages via TreeSitterParser (primary) with legacy BaseStrategy fallback.
    """
    # Production guard: skip files larger than 5 MB to avoid parser stalls / OOM
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
    PARSE_TIMEOUT_SECONDS = 15
    def __init__(self, db: DatabaseManager, codegraph_service=None):
        self.db = db
        self.codegraph_service = codegraph_service
        self.strategies: Dict[str, BaseStrategy] = {}
        # TreeSitterParser dispatch — primary path for all languages
        self._parser_cache: Dict[str, TreeSitterParser] = {}

        # Resource management: limit concurrent indexing tasks
        self._index_semaphore = asyncio.Semaphore(int(os.getenv("CODECORTEX_MAX_CONCURRENT_INDEXING", "10")))
        # Repository-level framework detector cache
        self._repo_detector_cache: Dict[str, RepositoryFrameworkDetector] = {}
        self.ts_parsers: Dict[str, str] = {
            ".py": "python",
            ".ipynb": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".hpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".java": "java",
            ".rb": "ruby",
            ".cs": "c_sharp",
            ".php": "php",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".scala": "scala",
            ".swift": "swift",
            ".hs": "haskell",
            ".dart": "dart",
            ".pl": "perl",
            ".pm": "perl",
            ".ex": "elixir",
            ".exs": "elixir",
        }

    def _get_repo_detector(self, repo_id: str, repo_root: Path) -> RepositoryFrameworkDetector:
        """Get or create a repository framework detector instance."""
        if repo_id not in self._repo_detector_cache:
            self._repo_detector_cache[repo_id] = RepositoryFrameworkDetector(repo_root)
        return self._repo_detector_cache[repo_id]

    def _enrich_frameworks(self, file_path: Path, parsed: Dict[str, Any], repo_id: str, repo_root: Path) -> Dict[str, Any]:
        """
        Trigger framework detection using repository-level context.
        Uses configuration files and multi-signal detection for maximum coverage.
        """
        suffix = file_path.suffix.lower()
        rel_path = str(file_path).replace("\\", "/").lower()
        imports = parsed.get("imports", [])
        classes = parsed.get("classes", [])
        functions = parsed.get("functions", [])
        source = parsed.get("source", "")
        
        # Get repository-level detector
        repo_detector = self._get_repo_detector(repo_id, repo_root)
        
        # Use repository detector for file-level enrichment
        enrichment = repo_detector.enrich_file(rel_path, source, imports, classes, functions)
        
        # Merge enrichment results into parsed data
        if enrichment.get("frameworks"):
            parsed["frameworks"] = enrichment["frameworks"]
        
        # Framework metadata is already applied to classes and functions by enrich_file
        return parsed

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        """Standardized structured logging."""
        log_payload = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "domain": "Domain.CodeIndex",
            "event_code": event_code,
            "context": context
        }
        if request_id:
            log_payload["request_id"] = request_id
            
        msg = f"[{event_code}] {json.dumps(context)}"
        extra = {"context": context}
        if request_id:
            extra["request_id"] = request_id
            
        if level == "ERROR":
            logger.error(msg, extra=extra)
        elif level == "WARN":
            logger.warning(msg, extra=extra)
        else:
            logger.info(msg, extra=extra)

    async def _record_insight(self, repo_id: str, category: str, insight_type: str, metadata: Dict[str, Any]) -> None:
        def _write():
            try:
                with self.db.transaction() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO insights (id, repository_id, target_code, category, insight_type, metadata)
                        VALUES (?, ?, NULL, ?, ?, ?)
                        """,
                        (str(uuid.uuid4()), repo_id, category, insight_type, json.dumps(metadata)),
                    )
            except Exception:
                pass
        await asyncio.to_thread(_write)

    def _get_parser(self, lang_name: str):
        """Return a cached TreeSitterParser, creating it on first use."""
        if lang_name not in self._parser_cache:
            self._parser_cache[lang_name] = TreeSitterParser(lang_name)
        return self._parser_cache[lang_name]

    async def _parse_with_timeout(self, parser, file_path: Path, **kwargs):
        """Run parser.parse with a cross-platform timeout guard using asyncio.to_thread."""
        try:
            # Use asyncio.wait_for to enforce timeout on the thread execution
            return await asyncio.wait_for(
                asyncio.to_thread(parser.parse, file_path, **kwargs),
                timeout=self.PARSE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            self._log_event(
                "WARN", "PARSE_TIMEOUT",
                {"path": str(file_path), "timeout_seconds": self.PARSE_TIMEOUT_SECONDS}
            )
            raise TimeoutError(
                f"Parsing timed out after {self.PARSE_TIMEOUT_SECONDS}s: {file_path}"
            ) from None
        except Exception as e:
            logger.error(f"Unexpected error during parse_with_timeout for {file_path}: {e}")
            raise

    async def index_repository(self, repo_id: str, request_id: Optional[str] = None):
        """
        Iterate through files and index them using TreeSitterParser (primary).
        Writes symbols to SQLite and, if a codegraph_service is injected,
        delegates graph backend sync to avoid duplicate parsing.
        """
        self._log_event("INFO", "REPO_INDEXING_STARTED", {"repository_id": repo_id}, request_id)

        def _get_root():
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            row = cursor.fetchone()
            return Path(row['root_path']) if row else None
        
        repo_root = await asyncio.to_thread(_get_root)
        if not repo_root:
            self._log_event("ERROR", "REPO_NOT_FOUND", {"repository_id": repo_id})
            return

        def _fetch_files():
            return self.db.conn.execute(
                """
                SELECT f.id AS id, f.name AS name, f.classification AS classification, d.relative_path AS dir_path
                FROM files f
                JOIN directories d ON d.id = f.directory_id
                WHERE f.repository_id = ?
                """,
                (repo_id,),
            ).fetchall()

        files = await asyncio.to_thread(_fetch_files)

        def _reset_repo():
            try:
                with self.db.transaction() as txn:
                    txn.execute(
                        "DELETE FROM symbols WHERE file_id IN (SELECT id FROM files WHERE repository_id = ?)",
                        (repo_id,),
                    )
                    txn.execute("DELETE FROM edges WHERE repository_id = ?", (repo_id,))
                    txn.execute("DELETE FROM insights WHERE repository_id = ? AND category = 'lint'", (repo_id,))
            except Exception as e:
                self._log_event("WARN", "REPO_INDEX_RESET_FAILED", {"repository_id": repo_id, "error": str(e)})

        await asyncio.to_thread(_reset_repo)

        indexed_count = 0
        parsed_files: List[Dict[str, Any]] = []
        # Pre-scan Python imports before indexing so graph sync batches are self-contained
        imports_map: Dict[str, Any] = {}
        if any(
            Path(f['name']).suffix.lower() in (".py", ".ipynb")
            for f in files
        ):
            try:
                imports_map = await self.pre_scan_repository(repo_id, request_id=request_id)
            except Exception as e:
                self._log_event("WARN", "PRE_SCAN_FAILED", {"repository_id": repo_id, "error": str(e)}, request_id)

        async def _process_file(f):
            nonlocal indexed_count
            if f["classification"] != "code":
                return
            dir_path = (f["dir_path"] or "").replace("\\", "/")
            file_rel_path = f"{dir_path}/{f['name']}" if dir_path else f["name"]
            file_path = repo_root / file_rel_path

            # Use thread for blocking file system check
            exists = await asyncio.to_thread(file_path.exists)
            if not exists:
                return
            
            stats = await asyncio.to_thread(file_path.stat)
            if stats.st_size > self.MAX_FILE_SIZE_BYTES:
                self._log_event("WARN", "FILE_TOO_LARGE_SKIPPED", {"path": file_rel_path, "size_bytes": stats.st_size}, request_id)
                return

            try:
                # Primary path: TreeSitterParser for all supported languages
                ext = file_path.suffix.lower()
                lang_name = self.ts_parsers.get(ext)
                if lang_name:
                    parsed = None
                    try:
                        parser = self._get_parser(lang_name)
                        is_notebook = ext == ".ipynb"
                        parsed = await self._parse_with_timeout(
                            parser, file_path, is_notebook=is_notebook, index_source=True
                        )
                    except ImportError as e:
                        if lang_name == "python" and ext == ".py":
                            parsed = await asyncio.to_thread(self._parse_python_builtin, file_path, file_rel_path)
                        else:
                            await self._record_insight(repo_id, "lint", "parser_unavailable", {"path": file_rel_path, "error": str(e)})
                            return

                    if parsed and "error" not in parsed:
                        # Enrich with framework metadata before persistence
                        parsed = await asyncio.to_thread(self._enrich_frameworks, file_path, parsed, repo_id, repo_root)
                        # Write to SQLite via converter
                        await self._write_parsed_to_sqlite(repo_id, f['id'], file_rel_path, parsed)
                        parsed_files.append(parsed)
                        indexed_count += 1
                    else:
                        reason = parsed.get("error") if parsed else "unknown_parse_error"
                        self._log_event("WARN", "TREE_SITTER_PARSE_EMPTY", {"path": file_rel_path, "reason": reason}, request_id)
                        await self._record_insight(repo_id, "lint", "syntax_error", {"path": file_rel_path, "error": reason})
                else:
                    # Fallback to legacy BaseStrategy path
                    def _read_and_index():
                        with open(file_path, "r", encoding="utf-8") as fh:
                            content = fh.read()
                        return self.index_file(repo_id, f['id'], file_rel_path, content)
                    
                    count = await asyncio.to_thread(_read_and_index)
                    if count:
                        indexed_count += 1
            except Exception as e:
                self._log_event("ERROR", "FILE_INDEX_FAILED", {"path": file_rel_path, "error": str(e)}, request_id)
                await self._record_insight(repo_id, "lint", "index_failed", {"path": file_rel_path, "error": str(e)})

        # Batch process with concurrency control
        tasks = []
        for f in files:
            async def _guarded_process(file_data=f):
                async with self._index_semaphore:
                    await _process_file(file_data)
            tasks.append(_guarded_process())
        
        await asyncio.gather(*tasks)

        # Graph backend sync — single pass to avoid duplicate edge risk
        if self.codegraph_service and parsed_files:
            try:
                await self.codegraph_service.write_repository_graph(repo_id, repo_root, parsed_files, imports_map)
                self._log_event("INFO", "GRAPH_SYNC_COMPLETED", {"repository_id": repo_id, "files": len(parsed_files)}, request_id)
            except Exception as e:
                self._log_event("ERROR", "GRAPH_SYNC_FAILED", {"repository_id": repo_id, "error": str(e)}, request_id)

        # SQLite-only edge resolution for cross-file call chains
        try:
            await asyncio.to_thread(self._resolve_edges_sqlite, repo_id)
        except Exception as e:
            self._log_event("ERROR", "SQLITE_EDGE_RESOLUTION_FAILED", {"repository_id": repo_id, "error": str(e)})

        self._log_event("INFO", "REPO_INDEXING_COMPLETED", {"repository_id": repo_id, "files_indexed": indexed_count})

    async def index_files(self, repo_id: str, relative_paths: List[str], request_id: Optional[str] = None) -> Dict[str, Any]:
        def _get_root():
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            return cursor.fetchone()
        
        row = await asyncio.to_thread(_get_root)
        if not row:
            raise ValueError(f"repository_not_found:{repo_id}")
        repo_root = Path(row["root_path"])

        relative_paths = [p for p in relative_paths if isinstance(p, str) and p.strip()]
        normalized = []
        for p in relative_paths:
            rp = p.strip().replace("\\", "/")
            if rp.startswith("./"):
                rp = rp[2:]
            normalized.append(rp.strip("/"))

        def _fetch_files():
            return self.db.conn.execute(
                """
                SELECT f.id AS file_id, f.name AS name, f.classification AS classification, d.relative_path AS dir_path
                FROM files f
                JOIN directories d ON d.id = f.directory_id
                WHERE f.repository_id = ?
                """,
                (repo_id,),
            ).fetchall()

        file_rows = await asyncio.to_thread(_fetch_files)
        rel_to_file: Dict[str, Dict[str, Any]] = {}
        for r in file_rows:
            dir_path = (r["dir_path"] or "").replace("\\", "/")
            rel = f"{dir_path}/{r['name']}" if dir_path else r["name"]
            rel_to_file[rel] = {"file_id": r["file_id"], "classification": r["classification"]}

        ids: List[tuple[str, str]] = []
        for rp in normalized:
            meta = rel_to_file.get(rp)
            if not meta or meta.get("classification") != "code":
                continue
            ids.append((meta["file_id"], rp))

        parsed_files: List[Dict[str, Any]] = []
        indexed_count = 0
        errors: List[Dict[str, Any]] = []

        async def _process_single(file_id, rp):
            nonlocal indexed_count
            abs_path = (repo_root / rp).resolve()
            if not str(abs_path).startswith(str(repo_root.resolve())):
                return
            
            exists = await asyncio.to_thread(abs_path.exists)
            if not exists:
                return
            
            stats = await asyncio.to_thread(abs_path.stat)
            if stats.st_size > self.MAX_FILE_SIZE_BYTES:
                self._log_event("WARN", "FILE_TOO_LARGE_SKIPPED", {"path": rp, "size_bytes": stats.st_size})
                return

            try:
                ext = abs_path.suffix.lower()
                lang_name = self.ts_parsers.get(ext)
                if lang_name:
                    parsed = None
                    try:
                        parser = self._get_parser(lang_name)
                        is_notebook = ext == ".ipynb"
                        parsed = await self._parse_with_timeout(parser, abs_path, is_notebook=is_notebook, index_source=True)
                    except ImportError as e:
                        if lang_name == "python" and ext == ".py":
                            parsed = await asyncio.to_thread(self._parse_python_builtin, abs_path, rp)
                        else:
                            await self._record_insight(repo_id, "lint", "parser_unavailable", {"path": rp, "error": str(e)})
                            return

                    if parsed and "error" not in parsed:
                        parsed = await asyncio.to_thread(self._enrich_frameworks, abs_path, parsed, repo_id, repo_root)
                        await self._write_parsed_to_sqlite(repo_id, file_id, rp, parsed)
                        parsed_files.append(parsed)
                        indexed_count += 1
                    else:
                        reason = parsed.get("error") if parsed else "unknown_parse_error"
                        await self._record_insight(repo_id, "lint", "syntax_error", {"path": rp, "error": reason})
                else:
                    try:
                        content = await asyncio.to_thread(abs_path.read_text, encoding="utf-8")
                        count = await asyncio.to_thread(self.index_file, repo_id, file_id, rp, content)
                        if count:
                            indexed_count += 1
                    except Exception:
                        pass
            except Exception as e:
                errors.append({"path": rp, "error": str(e)})
                await self._record_insight(repo_id, "lint", "index_failed", {"path": rp, "error": str(e)})

        # Concurrent processing with semaphore
        process_tasks = []
        for fid, rp in ids:
            async def _guarded(fid=fid, rp=rp):
                async with self._index_semaphore:
                    await _process_single(fid, rp)
            process_tasks.append(_guarded())
        
        await asyncio.gather(*process_tasks)

        imports_map: Dict[str, Any] = {}
        if any(Path(p).suffix.lower() in (".py", ".ipynb") for p in normalized):
            try:
                imports_map = await self.pre_scan_repository(repo_id, request_id=request_id)
            except Exception:
                imports_map = {}

        if self.codegraph_service and parsed_files:
            try:
                await self.codegraph_service.write_repository_graph(repo_id, repo_root, parsed_files, imports_map)
                self._log_event("INFO", "GRAPH_SYNC_COMPLETED", {"repository_id": repo_id, "files": len(parsed_files)})
            except Exception as e:
                self._log_event("ERROR", "GRAPH_SYNC_FAILED", {"repository_id": repo_id, "error": str(e)})

        try:
            await asyncio.to_thread(self._resolve_edges_sqlite, repo_id)
        except Exception as e:
            self._log_event("ERROR", "SQLITE_EDGE_RESOLUTION_FAILED", {"repository_id": repo_id, "error": str(e)})

        if indexed_count:
            def _update_manifest():
                try:
                    with self.db.transaction() as txn:
                        for _, rp in ids:
                            rp_back = rp.replace("/", "\\")
                            txn.execute(
                                """
                                UPDATE manifest_entries
                                SET last_processed_at = CURRENT_TIMESTAMP
                                WHERE repository_id = ? AND file_path IN (?, ?)
                                """,
                                (repo_id, rp, rp_back),
                            )
                except Exception:
                    pass
            await asyncio.to_thread(_update_manifest)

        return {"files_requested": len(normalized), "files_indexed": indexed_count, "errors": errors}

    async def _write_parsed_to_sqlite(self, repo_id: str, file_id: str, file_rel_path: str, parsed: Dict[str, Any]) -> int:
        raw_symbols = parsed_data_to_raw_symbols(file_rel_path, parsed)
        return await self._persist_raw_symbols(repo_id, file_id, raw_symbols)

    async def _persist_raw_symbols(self, repo_id: str, file_id: str, raw_symbols: List[RawSymbol]) -> int:
        """Core SQLite write for RawSymbols with two-pass parent resolution."""
        if not raw_symbols:
            return 0

        def _write():
            code_to_uuid: Dict[str, str] = {}
            try:
                with self.db.transaction() as cursor:
                    cursor.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))

                    # First pass: insert with temporary parent code_ref
                    for raw in raw_symbols:
                        symbol_id = str(uuid.uuid4())
                        if raw.code_ref:
                            code_to_uuid[raw.code_ref] = symbol_id

                        meta = json.dumps({
                            "variables": raw.variables if raw.variables else [],
                            "function_calls": raw.function_calls if raw.function_calls else [],
                            "imports": raw.imports if raw.imports else [],
                            "language": raw.language,
                        }) if (raw.variables or raw.function_calls or raw.imports or raw.language) else None

                        cursor.execute("""
                            INSERT INTO symbols (id, repository_id, file_id, parent_id, code, name, symbol_type, start_line, end_line, docstring, signature, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            symbol_id, repo_id, file_id, None, raw.code_ref, raw.name,
                            raw.symbol_type, raw.start_line, raw.end_line,
                            raw.docstring, raw.signature, meta
                        ))

                    # Second pass: resolve parent_id UUIDs
                    for raw in raw_symbols:
                        if raw.parent_id and raw.parent_id in code_to_uuid:
                            parent_uuid = code_to_uuid[raw.parent_id]
                            symbol_uuid = code_to_uuid.get(raw.code_ref)
                            if symbol_uuid:
                                cursor.execute("UPDATE symbols SET parent_id = ? WHERE id = ?", (parent_uuid, symbol_uuid))
                return len(raw_symbols)
            except Exception as e:
                self._log_event("ERROR", "SQLITE_WRITE_FAILED", {"file_id": file_id, "error": str(e)})
                return 0
        
        return await asyncio.to_thread(_write)

    def index_file(self, repo_id: str, file_id: str, file_rel_path: str, content: str):
        """
        Legacy BaseStrategy path. Retained for backward compatibility.
        New code should use TreeSitterParser via index_repository().
        """
        ext = Path(file_rel_path).suffix.lower()
        strategy = self.strategies.get(ext)

        if not strategy:
            return 0

        try:
            raw_symbols = strategy.parse(content, file_rel_path)
            return self._persist_raw_symbols(repo_id, file_id, raw_symbols)
        except Exception as e:
            self._log_event("ERROR", "AST_PARSE_FAILED", {"path": file_rel_path, "error": str(e)})
            return 0

    async def index_file_with_tree_sitter(self, repo_id: str, file_id: str, file_path: Path, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Index a file using TreeSitterParser for richer AST extraction.
        Writes symbols to SQLite and returns the parsed data dict.
        """
        ext = file_path.suffix.lower()
        lang_name = self.ts_parsers.get(ext)

        if not lang_name:
            return {"error": f"Unsupported file extension: {ext}"}
        
        stats = await asyncio.to_thread(file_path.stat)
        if stats.st_size > self.MAX_FILE_SIZE_BYTES:
            self._log_event("WARN", "FILE_TOO_LARGE_SKIPPED", {"path": str(file_path), "size_bytes": stats.st_size})
            return {"error": "file_too_large"}

        try:
            parser = self._get_parser(lang_name)
            is_notebook = file_path.suffix.lower() == ".ipynb"
            parsed_data = await self._parse_with_timeout(
                parser, file_path, is_notebook=is_notebook, index_source=True
            )
            if "error" not in parsed_data:
                def _get_root():
                    cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                    return Path(cursor.fetchone()["root_path"])
                
                repo_root = await asyncio.to_thread(_get_root)
                parsed_data = await asyncio.to_thread(self._enrich_frameworks, file_path, parsed_data, repo_id, repo_root)
                file_rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
                await self._write_parsed_to_sqlite(repo_id, file_id, file_rel_path, parsed_data)
            else:
                await self._record_insight(repo_id, "lint", "syntax_error", {"path": str(file_path), "error": parsed_data.get("error")})
            return parsed_data
        except Exception as e:
            self._log_event("ERROR", "TREE_SITTER_PARSE_FAILED", {"path": str(file_path), "error": str(e)})
            await self._record_insight(repo_id, "lint", "index_failed", {"path": str(file_path), "error": str(e)})
            return {"error": str(e)}

    async def pre_scan_repository(self, repo_id: str, request_id: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Pre-scan Python files to build imports_map for call resolution.
        Returns dict mapping symbol names to their file paths.
        """
        def _get_files():
            cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
            repo_root = Path(cursor.fetchone()['root_path'])

            files_data = self.db.conn.execute(
                """
                SELECT f.id AS id, f.name AS name, d.relative_path AS dir_path
                FROM files f
                JOIN directories d ON d.id = f.directory_id
                WHERE f.repository_id = ?
                """,
                (repo_id,),
            ).fetchall()
            return repo_root, files_data

        repo_root, files = await asyncio.to_thread(_get_files)

        python_files: List[Path] = []
        for f in files:
            dir_path = (f["dir_path"] or "").replace("\\", "/")
            file_rel = f"{dir_path}/{f['name']}" if dir_path else f["name"]
            file_path = repo_root / file_rel
            
            # Thread check for existence and size
            exists = await asyncio.to_thread(file_path.exists)
            if exists and file_path.suffix.lower() in [".py", ".ipynb"]:
                stats = await asyncio.to_thread(file_path.stat)
                if stats.st_size <= self.MAX_FILE_SIZE_BYTES:
                    python_files.append(file_path)
                else:
                    self._log_event("WARN", "PRE_SCAN_FILE_TOO_LARGE", {"path": str(file_path), "size_bytes": stats.st_size})

        if not python_files:
            return {}

        try:
            parser_wrapper = self._get_parser("python")
            imports_map = await asyncio.to_thread(pre_scan_python, python_files, parser_wrapper)
        except Exception:
            return {}
        self._log_event(
            "INFO",
            "PRE_SCAN_COMPLETED",
            {"repository_id": repo_id, "python_files": len(python_files), "symbols_mapped": len(imports_map)},
        )
        return imports_map

    def _parse_python_builtin(self, file_path: Path, file_rel_path: str) -> Dict[str, Any]:
        try:
            src = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return {"path": file_rel_path, "error": str(e)}

        try:
            tree = ast.parse(src, filename=file_rel_path)
        except SyntaxError as e:
            return {"path": file_rel_path, "error": f"syntax_error:{e.msg}:{e.lineno}:{e.offset}"}

        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []

        def _call_name(n: ast.AST) -> Optional[str]:
            if isinstance(n, ast.Name):
                return n.id
            if isinstance(n, ast.Attribute):
                return n.attr
            return None

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({"name": alias.name, "source": alias.name, "alias": alias.asname, "line_number": getattr(node, "lineno", 1), "lang": "python"})
                else:
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append({"name": alias.name, "source": mod, "alias": alias.asname, "line_number": getattr(node, "lineno", 1), "lang": "python"})

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases: List[str] = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        bases.append(b.attr)
                classes.append(
                    {
                        "name": node.name,
                        "line_number": getattr(node, "lineno", 1),
                        "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                        "bases": bases,
                        "docstring": ast.get_docstring(node),
                        "lang": "python",
                        "is_dependency": False,
                    }
                )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args] if getattr(node, "args", None) else []
                fn_name = node.name
                calls: List[Dict[str, Any]] = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        nm = _call_name(sub.func)
                        if nm:
                            calls.append({"name": nm, "line_number": getattr(sub, "lineno", 1)})
                functions.append(
                    {
                        "name": fn_name,
                        "line_number": getattr(node, "lineno", 1),
                        "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                        "args": args,
                        "docstring": ast.get_docstring(node),
                        "function_calls": calls,
                        "lang": "python",
                        "is_dependency": False,
                    }
                )

        return {
            "path": file_rel_path,
            "functions": functions,
            "classes": classes,
            "variables": [],
            "imports": imports,
            "function_calls": [],
            "is_dependency": False,
            "lang": "python",
        }

    def _resolve_edges_sqlite(self, repo_id: str) -> None:
        """
        Resolve deferred cross-file calls and write CALLS edges into SQLite.
        Ported from legacy sqlite_index_builder._resolve_pending_calls_sqlite.
        """
        cursor = self.db.conn.execute(
            "SELECT id, name, symbol_type, code, metadata FROM symbols WHERE file_id IN "
            "(SELECT id FROM files WHERE repository_id = ?)", (repo_id,)
        )
        rows = cursor.fetchall()
        if not rows:
            return

        # Build name -> [symbol_id] lookup
        name_to_ids: Dict[str, List[str]] = {}
        id_to_type: Dict[str, str] = {}
        for row in rows:
            sid = row["id"]
            name = row["name"]
            name_to_ids.setdefault(name, []).append(sid)
            id_to_type[sid] = row["symbol_type"]

        # Collect pending calls from symbol metadata JSON
        pending: List[tuple] = []
        for row in rows:
            if row["symbol_type"] != "function":
                continue
            meta_raw = row["metadata"]
            if not meta_raw:
                continue
            try:
                meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                calls = meta.get("function_calls", [])
                if not isinstance(calls, list):
                    continue
                for c in calls:
                    callee_name = c.get("name") if isinstance(c, dict) else None
                    if callee_name:
                        pending.append((row["id"], callee_name))
            except Exception:
                continue

        if not pending:
            return

        edges_inserted = 0
        with self.db.transaction() as txn:
            # Clear old CALLS edges for this repo to avoid stale data
            txn.execute("DELETE FROM edges WHERE repository_id = ? AND relation_type = 'CALLS'", (repo_id,))
            for source_id, callee_name in pending:
                target_ids = name_to_ids.get(callee_name, [])
                for tid in target_ids:
                    if tid == source_id:
                        continue  # skip self-calls to keep graph lean
                    edge_id = f"{source_id}--{tid}--CALLS"
                    txn.execute(
                        """
                        INSERT INTO edges (id, repository_id, source_id, target_id, relation_type, weight)
                        VALUES (?, ?, ?, ?, 'CALLS', 1.0)
                        ON CONFLICT(id) DO UPDATE SET weight = weight + 1.0
                        """,
                        (edge_id, repo_id, source_id, tid),
                    )
                    edges_inserted += 1
        self._log_event("INFO", "SQLITE_EDGES_RESOLVED", {"repository_id": repo_id, "edges_inserted": edges_inserted})

    def search_symbols(self, repo_id: str, query: str, is_regex: bool = False) -> List[Dict[str, Any]]:
        """
        Search for symbols across the repository with literal or regex filtering.
        Aegis 4.1 compliant: includes file context and relative paths.
        """
        op = "REGEXP" if is_regex else "LIKE"
        search_pattern = query if is_regex else f"%{query}%"

        sql = f"""
            SELECT 
                s.id, s.name, s.symbol_type, s.start_line, s.end_line, 
                f.name as file_name, d.relative_path
            FROM symbols s
            JOIN files f ON f.id = s.file_id
            JOIN directories d ON d.id = f.directory_id
            WHERE s.repository_id = ? AND s.name {op} ?
            ORDER BY s.name ASC
            LIMIT 100
        """
        
        try:
            cursor = self.db.conn.execute(sql, (repo_id, search_pattern))
            results = [dict(row) for row in cursor.fetchall()]
            self._log_event("INFO", "SYMBOL_SEARCH_COMPLETED", {
                "repo_id": repo_id, "query": query, "hits": len(results)
            })
            return results
        except Exception as e:
            self._log_event("ERROR", "SYMBOL_SEARCH_FAILED", {
                "repo_id": repo_id, "query": query, "error": str(e)
            })
            return []
