"""
/**
 * @project   CodeCortex
 * @package   Main
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class CortexOrchestrator – Single Responsibility: Orchestrate the multi-domain intelligence pipeline.
 */
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP

from src.core import api_response, new_request_id
from src.core.logging_config import LoggerConfig, get_logger
from src.core.database import DatabaseManager
from src.domain.coderepository import CodeRepositoryService, GitService
from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
from src.domain.codeindex import CodeIndexService
from src.domain.codegraph import CodeGraphService
from src.domain.filesystem.application.service import FilesystemService
from src.domain.coderefactor import CodeRefactorService
from src.domain.codetester.application.qa_service import QAService
from src.core.telemetry import trace  # OpenTelemetry tracing

# Initialize FastMCP Server
mcp = FastMCP("CodeCortex")

# Initialize logging
LoggerConfig.setup(log_level="INFO")
logger = get_logger(__name__)

class CortexOrchestrator:
    """
    Main orchestrator for CodeCortex.

    Standardizes the flow between Repository, CodeIndex, CodeGraph, and Graphify.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db = DatabaseManager(db_path)
        self.repo_store = SQLiteCodeRepositoryStore(self.db)
        self.repo_service = CodeRepositoryService(self.repo_store)
        self.graph_service = CodeGraphService(self.db)
        self.index_service = CodeIndexService(self.db, codegraph_service=self.graph_service)
        self.graph_service.code_index_service = self.index_service
        self.fs_service = FilesystemService(self.db, self.repo_store)
        self.git_service = GitService(self.repo_store)
        self.refactor_service = CodeRefactorService(self.db, self.fs_service, self.git_service, self.graph_service)
        self.qa_service = QAService(self.db)
        self.logger = get_logger(f"{__name__}.Orchestrator")

    def get_repo_id(self, path: str) -> Optional[str]:
        """Resolve a physical path to its repository ID in the database."""
        root = Path(path).resolve()
        cursor = self.db.conn.execute("SELECT id FROM repositories WHERE root_path = ?", (str(root),))
        row = cursor.fetchone()
        return row['id'] if row else None

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        """Standardized structured logging per Aegis standard."""
        log_level = getattr(logging, level.upper(), logging.INFO)
        extra = {"context": context}
        if request_id:
            extra["request_id"] = request_id
        self.logger.log(log_level, f"{event_code}", extra=extra)

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
        
        @param root_path: Absolute path to the repository
        @param request_id: Optional tracing ID
        @param dry_run: If True (default), skip DB mutations (sync/index) and analyze existing data.
                        Set False to perform a full refresh of the index before analysis.
        @param max_depth: Optional recursion limit for file discovery.
        @param include_codemap: If True, includes a structured symbol map in the response.
        @param max_repos: Quota limit for concurrent repository analysis.
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
                "SELECT id, name, relative_path FROM directories WHERE repository_id = ? ORDER BY relative_path",
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

# --- Input Validation ---
def validate_path(path: str) -> tuple[bool, str]:
    """
    Validate that a path is safe and exists.

    Returns (is_valid, error_message)
    """
    if not path or not isinstance(path, str):
        return False, "Path must be a non-empty string"

    if ".." in path:
        return False, "Path traversal detected"

    try:
        resolved_path = Path(path).resolve()
        if not resolved_path.exists():
            return False, f"Path does not exist: {path}"
        if not resolved_path.is_dir():
            return False, f"Path is not a directory: {path}"
        return True, ""
    except Exception as e:
        return False, f"Invalid path: {str(e)}"

def validate_uuid(uuid_str: str) -> tuple[bool, str]:
    """
    Validate that a string is a valid UUID.

    Returns (is_valid, error_message)
    """
    if not uuid_str or not isinstance(uuid_str, str):
        return False, "UUID must be a non-empty string"

    try:
        from uuid import UUID
        UUID(uuid_str)
        return True, ""
    except ValueError:
        return False, f"Invalid UUID format: {uuid_str}"

def validate_max_depth(depth: int) -> tuple[bool, str]:
    """
    Validate max_depth parameter.

    Returns (is_valid, error_message)
    """
    if not isinstance(depth, int):
        return False, "max_depth must be an integer"
    if depth < 1 or depth > 20:
        return False, "max_depth must be between 1 and 20"
    return True, ""

def _normalize_relpath(root: Path, p: str) -> Optional[str]:
    if not isinstance(p, str) or not p.strip():
        return None
    raw = p.strip().replace("\\", "/")
    if raw.startswith("./"):
        raw = raw[2:]
    try:
        pp = Path(p)
        if pp.is_absolute():
            rel = pp.resolve().relative_to(root.resolve())
            return str(rel).replace("\\", "/")
        return str(Path(raw)).replace("\\", "/").strip("/")
    except Exception:
        return None

# --- MCP Tool Registration ---

# Register Domain Tools
from src.domain.codegraph.api.tools import register_tools as register_graph_tools
from src.domain.coderepository.api.tools import register_tools as register_repository_tools
from src.domain.filesystem.api.tools import register_tools as register_fs_tools
from src.domain.coderefactor.api.tools import register_tools as register_refactor_tools
from src.domain.codetester.api.tools import register_tools as register_qa_tools
from src.domain.codeindex.api.tools import register_tools as register_index_tools

# Orchestrator factory function - no global singleton
def create_orchestrator(db_path: Optional[str] = None) -> CortexOrchestrator:
    """
    Factory function to create orchestrator instances.
    
    Follows Aegis modular-standard.md requirement for DI and no global state.
    Each tool handler creates its own orchestrator instance, ensuring proper
    lifecycle management and testability.
    """
    return CortexOrchestrator(db_path)

# Initialize Domain Tools
register_fs_tools(mcp, create_orchestrator)
register_refactor_tools(mcp, create_orchestrator)
register_graph_tools(mcp, create_orchestrator)
register_repository_tools(mcp, create_orchestrator)
register_qa_tools(mcp, create_orchestrator)
register_index_tools(mcp, create_orchestrator)

# All tools are now registered via domain-specific modules for better cohesion and performance.

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
