"""
CodeCortex MCP Server — Main entry point.

:project: CodeCortex
:package: Main
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CrossStack-v1.0
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP

from src.core import api_response, new_request_id
from src.core.logging import Logger, get_logger
from src.core.logging.event_logger import log_event
from src.core.database import DatabaseManager
from src.core.utils.validators import validate_path, validate_uuid, validate_max_depth
from src.core.utils.path import normalize_relpath as _normalize_relpath
from src.modules.coderepository import Repository, Git, Svn
from src.modules.coderepository.adapters.filesystem.sqlite_store import SQLiteCodeRepositoryStore
from src.modules.codeindex import Indexer
from src.modules.codegraph import Graph
from src.modules.codeanalysis.core.code_service import CodeService
from src.modules.filesystem.core.service import Filesystem
from src.modules.coderefactor import Refactor
from src.modules.codetester.services.qa import QA
from src.core.telemetry import get_tracer_provider  # OpenTelemetry tracing (lazy init)

# Initialize FastMCP Server
mcp = FastMCP("CodeCortex")

# Initialize logging
Logger.setup(log_level="INFO")
logger = get_logger(__name__)

class CortexOrchestrator:
    """
    Main orchestrator for CodeCortex.

    Standardizes the flow between Repository, CodeIndex, CodeGraph, and Graphify.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db = DatabaseManager(db_path)
        self._ensure_schema()
        self.repo_store = SQLiteCodeRepositoryStore(self.db)
        self.repo_service = Repository(self.repo_store)
        self.graph_service = Graph(self.db)
        self.index_service = Indexer(self.db, codegraph_service=self.graph_service)
        self.graph_service.code_index_service = self.index_service
        self.git_service = Git(self.repo_store)
        self.svn_service = Svn()
        self.qa_service = QA(self.db)
        self.fs_service = Filesystem(
            self.db, self.repo_store,
            graph_service=self.graph_service,
            index_service=self.index_service,
            git_service=self.git_service,
            svn_service=self.svn_service,
            qa_service=self.qa_service,
        )
        self.refactor_service = Refactor(self.db, self.fs_service, self.git_service, self.graph_service)
        self.code_service = CodeService(self)
        self.logger = get_logger(f"{__name__}.Orchestrator")

    def _ensure_schema(self) -> None:
        """Create database tables if they do not exist (idempotent)."""
        from src.core.database.orm import BaseModel, SessionManager
        SessionManager(str(self.db._db_path)).create_tables(BaseModel)
        # Ensure vcs_url uniqueness index for cross-device identity
        self.db.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_repositories_vcs_url
            ON repositories(vcs_url) WHERE vcs_url IS NOT NULL AND vcs_url != ''
        """)
        # Ensure deleted_at column exists (ORM model has it, raw SQL create may miss it)
        try:
            self.db.conn.execute("ALTER TABLE repositories ADD COLUMN deleted_at DATETIME")
        except Exception:
            pass
        # Ensure missing columns on legacy files table
        _FILE_MISSING_COLS = {
            "relative_path": "TEXT",
            "directory_id": "TEXT",
            "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "deleted_at": "DATETIME",
            "language": "TEXT DEFAULT 'unknown'",
        }
        existing = {r[1] for r in self.db.conn.execute("PRAGMA table_info(files)").fetchall()}
        for col, coltype in _FILE_MISSING_COLS.items():
            if col not in existing:
                try:
                    self.db.conn.execute(f"ALTER TABLE files ADD COLUMN {col} {coltype}")
                except Exception:
                    pass
        _SYMBOL_MISSING_COLS = {
            "parent_id": "TEXT",
        }
        existing = {r[1] for r in self.db.conn.execute("PRAGMA table_info(symbols)").fetchall()}
        for col, coltype in _SYMBOL_MISSING_COLS.items():
            if col not in existing:
                try:
                    self.db.conn.execute(f"ALTER TABLE symbols ADD COLUMN {col} {coltype}")
                except Exception:
                    pass
        # Ensure missing tables used by raw SQL queries
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                repository_id TEXT NOT NULL,
                target_code TEXT,
                category TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.conn.execute("CREATE INDEX IF NOT EXISTS idx_insights_repo ON insights(repository_id)")
        self.db.conn.execute("CREATE INDEX IF NOT EXISTS idx_insights_category ON insights(category)")
        # Path mapping tables for remote server cross-device support
        from src.core.database.path_mapping import PATH_MAPPING_DDL
        for ddl in PATH_MAPPING_DDL:
            self.db.conn.execute(ddl)
        self.db.conn.commit()
        # SideCortex cross-IDE tables (sc_ prefix)
        from src.core.database.sidecortex_schema import ensure_sidecortex_tables
        ensure_sidecortex_tables(self.db.conn)

    def get_repo_id(self, path: str) -> Optional[str]:
        """Resolve a physical path to its repo ID. Falls back to remote_url matching for cross-device."""
        import subprocess, os
        root = Path(path).resolve()
        row = self.db.conn.execute("SELECT id FROM repositories WHERE root_path = ?", (str(root),)).fetchone()
        if row:
            return row['id']
        remote_url = None
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                remote_url = result.stdout.strip()
        except Exception:
            pass
        if remote_url:
            row = self.db.conn.execute(
                "SELECT id FROM repositories WHERE vcs_url = ? AND vcs_url IS NOT NULL AND vcs_url != ''",
                (remote_url,),
            ).fetchone()
            return row['id'] if row else None
        return None

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        log_event(level, event_code, context, request_id=request_id, logger=self.logger)

    async def analyze(
        self,
        root_path: str,
        request_id: Optional[str] = None,
        dry_run: bool = True,
        max_depth: Optional[int] = None,
        include_codemap: bool = False,
        max_repos: int = 50
    ) -> Dict[str, Any]:
        """
        Execute the full intelligence pipeline with production guards.

        Args:
            root_path: Absolute path to the repository.
            request_id: Optional tracing ID for observability.
            dry_run: If True (default), skip DB mutations and analyze existing data.
                     Set False to perform a full refresh of the index before analysis.
            max_depth: Optional recursion limit for file discovery.
            include_codemap: If True, includes a structured symbol map in the response.
            max_repos: Quota limit for concurrent repository analysis.

        Returns:
            Dict with repository_id, analysis, codemap, and mode.
        """
        self._log_event("INFO", "ANALYSIS_STARTED", {"root_path": root_path, "dry_run": dry_run, "max_depth": max_depth}, request_id)
        try:
            repo_id = self.get_repo_id(root_path)

            if not dry_run:
                # 1. Physical Discovery (Mutating)
                repo_id = await self.repo_service.sync_repository(root_path, request_id=request_id, max_depth=max_depth)

                # 2. Semantic Indexing (AST) + Graph Sync (Mutating)
                await self.index_service.index_repository(repo_id, request_id=request_id)
            else:
                if not repo_id:
                    raise ValueError(f"Repository at {root_path} has not been initialized. Please run with dry_run=False first to create the initial index.")

            # 3. Architectural Analysis (Unified CodeGraph - Read-only)
            analysis = await self.graph_service.build_comprehensive_report(repo_id, request_id=request_id)

            # 4. Optional Codemap (Read-only)
            codemap = None
            if include_codemap:
                codemap = await self._build_codemap(repo_id)

            self._log_event("INFO", "ANALYSIS_COMPLETED", {"repository_id": repo_id, "dry_run": dry_run}, request_id)
            return {
                "repository_id": repo_id,
                "analysis": analysis,
                "codemap": codemap,
                "mode": "dry_run" if dry_run else "full_refresh"
            }
        except Exception as e:
            self._log_event("ERROR", "ANALYSIS_FAILED", {"error": str(e)}, request_id)
            raise

    async def _build_codemap(self, repo_id: str) -> Dict[str, Any]:
        """Internal helper to build a structured map of folders, files, and symbols."""
        def _execute():
            # 1. Get all directories
            dirs = self.db.conn.execute(
                "SELECT id, relative_path FROM directories WHERE repository_id = ? ORDER BY relative_path",
                (repo_id,)
            ).fetchall()

            # 2. Get all files
            files = self.db.conn.execute(
                "SELECT id, name, directory_id FROM files WHERE repository_id = ?",
                (repo_id,)
            ).fetchall()

            # 3. Get all key symbols (classes and functions)
            symbols = self.db.conn.execute(
                "SELECT id, name, symbol_type, file_id FROM symbols WHERE repository_id = ? AND symbol_type IN ('class', 'function')",
                (repo_id,)
            ).fetchall()

            # Map construction
            tree = {}
            file_symbols = {}
            for s in symbols:
                f_id = s['file_id']
                if f_id not in file_symbols: file_symbols[f_id] = []
                file_symbols[f_id].append({"id": s['id'], "name": s['name'], "type": s['symbol_type']})

            dir_files = {}
            for f in files:
                d_id = f['directory_id']
                if d_id not in dir_files: dir_files[d_id] = []
                dir_files[d_id].append({
                    "id": f['id'],
                    "name": f['name'],
                    "symbols": file_symbols.get(f['id'], [])
                })

            for d in dirs:
                tree[d['relative_path'] or "."] = dir_files.get(d['id'], [])
            return tree

        return await self.graph_service.run_in_thread(_execute)

# --- MCP Tool Wrapper ---
def _ok(message: str, data: Any, request_id: str) -> Dict[str, Any]:
    return api_response(success=True, status_code=200, message=message, data=data, request_id=request_id)

def _err(message: str, error_code: str, request_id: str, status_code: int = 400) -> Dict[str, Any]:
    return api_response(success=False, status_code=status_code, message=message, data=None, request_id=request_id, error_code=error_code)

# --- Tool Registration ---
# 5 unified MCP tools — all domain capabilities accessed via action+args dispatch.
# - codecortex:repository    (13 actions: init, inspect, analyze, sync, audit, ...)
# - codecortex:filesystem    (11 actions: read, write, delete, copy, move, search, ...)
# - codecortex:codebase      (8 actions: analyze, search, audit, graph, index, ...)
# - codecortex:scaffolder    (7 actions: list_stacks, get_stack, validate_name, ...)
# - codecortex:knowledge     (4 actions: extract, query, status, relationships)

from src.api.tools import register_tools as register_api_tools
from src.modules.knowledgegraph.api.tools import register_tools as register_knowledge_tools
from src.modules.idegraph.api.tools import register_tools as register_idegraph_tools

def create_orchestrator(db_path: Optional[str] = None) -> CortexOrchestrator:
    """
    Factory function to create orchestrator instances.

    Follows Aegis modular-standard.md requirement for DI and no global state.
    Each tool handler creates its own orchestrator instance, ensuring proper
    lifecycle management and testability.
    """
    return CortexOrchestrator(db_path)

# Unified API Tools Only (4 tools — action+args dispatch to all capabilities)
# All domain capabilities are accessed through these 4 tools via ActionRouter.
# Individual domain tools (code_analyze, graph_search, etc.) are NOT registered
# as MCP tools — they remain as internal service modules callable by ActionRouter
# and CLI.
register_api_tools(mcp, create_orchestrator)

# Register Knowledge Graph tool (5th tool)
register_knowledge_tools(mcp, create_orchestrator)

# Register IDE Graph tool (6th tool)
register_idegraph_tools(mcp, create_orchestrator)

# Total: 6 unified MCP tools

if __name__ == "__main__":
    import sys

    transport = os.getenv("CODECORTEX_TRANSPORT", "stdio").strip().lower()

    if transport in ("sse", "http"):
        # Launching the FastAPI wrapper (defined in http_server.py)
        # We import it here to avoid circular dependencies
        from scripts.server.http import main as run_server
        run_server()
    else:
        # Standard MCP Stdio transport
        mcp.run()
