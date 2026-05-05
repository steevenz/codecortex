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
        # Wire graph ↔ index bidirectionally so pre_scan + graph sync are shared
        self.graph_service = CodeGraphService(self.db)
        self.index_service = CodeIndexService(self.db, codegraph_service=self.graph_service)
        self.graph_service.code_index_service = self.index_service

        self.fs_service = FilesystemService(self.db, self.repo_store)
        self.git_service = GitService(self.repo_store)
        self.refactor_service = CodeRefactorService(
            self.db, 
            self.fs_service, 
            self.git_service, 
            self.graph_service
        )
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

    async def analyze(self, root_path: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute the full intelligence pipeline with production guards."""
        self._log_event("INFO", "ANALYSIS_STARTED", {"root_path": root_path}, request_id)
        try:
            # 1. Physical Discovery
            repo_id = await self.repo_service.sync_repository(root_path, request_id=request_id)

            # 2. Semantic Indexing (AST) + Graph Sync (unified)
            await self.index_service.index_repository(repo_id, request_id=request_id)

            # 3. Architectural Analysis (Unified CodeGraph)
            analysis = await self.graph_service.build_comprehensive_report(repo_id, request_id=request_id)

            self._log_event("INFO", "ANALYSIS_COMPLETED", {"repository_id": repo_id}, request_id)
            return {
                "repository_id": repo_id,
                "analysis": analysis
            }
        except Exception as e:
            self._log_event("ERROR", "ANALYSIS_FAILED", {"error": str(e)}, request_id)
            raise

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

# --- Top-Level Pipeline Tools ---

@mcp.tool()
async def analyze_codebase(path: str) -> Dict[str, Any]:
    """
    Perform a deep, multi-dimensional analysis of a codebase.
    Returns unified intelligence envelope.
    """
    request_id = new_request_id()
    is_valid, error_msg = validate_path(path)
    if not is_valid:
        return _err(error_msg, "VAL_001", request_id, status_code=422)

    orchestrator = create_orchestrator()
    try:
        result = await orchestrator.analyze(path, request_id=request_id)
        return _ok("Codebase analysis completed", result, request_id)
    except Exception as e:
        return _err(f"Codebase analysis failed: {str(e)}", "SRV_001", request_id, status_code=500)
    finally:
        try:
            orchestrator.db.close()
        except Exception:
            pass

@mcp.tool()
async def search_symbols(path: str, query: str, is_regex: bool = False, limit: int = 100) -> Dict[str, Any]:
    """
    Search for symbols across the codebase by name.
    Supports literal and regex queries.
    """
    request_id = new_request_id()
    is_valid, error_msg = validate_path(path)
    if not is_valid:
        return _err(error_msg, "VAL_001", request_id, status_code=422)

    if not query or not isinstance(query, str):
        return _err("Query must be a non-empty string", "VAL_003", request_id, status_code=422)

    orchestrator = create_orchestrator()
    try:
        repo_id = orchestrator.get_repo_id(path)
        if not repo_id:
            # Auto-sync if repository not yet indexed
            repo_id = await orchestrator.repo_service.sync_repository(path)
            await orchestrator.index_service.index_repository(repo_id, request_id=request_id)

        hits = await asyncio.to_thread(orchestrator.index_service.search_symbols, repo_id, query, is_regex=is_regex, limit=limit)
        return _ok(f"Symbol search completed: {len(hits)} hits", {"hits": hits}, request_id)
    except Exception as e:
        return _err(f"Symbol search failed: {str(e)}", "SRV_002", request_id, status_code=500)
    finally:
        try:
            orchestrator.db.close()
        except Exception:
            pass

@mcp.tool()
async def get_architecture_summary(path: str) -> Dict[str, Any]:
    """
    Fetch a high-craft architectural summary of the codebase.
    Includes: Vital metrics, God Nodes, Temporal Hotspots, Module Dependencies, and Inquiry.

    @param path: Absolute path to the repository root.
    """
    request_id = new_request_id()
    is_valid, error_msg = validate_path(path)
    if not is_valid:
        return _err(error_msg, "VAL_001", request_id, status_code=422)

    orchestrator = create_orchestrator()
    try:
        repo_id = orchestrator.get_repo_id(path)

        # Auto-sync if not found
        if not repo_id:
            repo_id = await orchestrator.repo_service.sync_repository(path)
            await orchestrator.index_service.index_repository(repo_id)

        # Generate raw data report
        data = await orchestrator.graph_service.build_comprehensive_report(repo_id)

        # Generate human-readable markdown
        markdown = data.get("summary", "") # build_comprehensive_report already generates markdown in 'summary'

        return _ok(
            "Architectural summary generated successfully",
            {
                "markdown": markdown,
                "raw_data": data
            },
            request_id
        )
    except Exception as e:
        logger.error(f"Architecture summary failed: {e}", exc_info=True)
        return _err(f"Architecture summary failed: {str(e)}", "SRV_003", request_id, status_code=500)
    finally:
        try:
            orchestrator.db.close()
        except Exception:
            pass

@mcp.tool()
async def trace_execution_flow(start_symbol_id: str, max_depth: int = 5) -> Dict[str, Any]:
    """
    Recursively trace the call graph starting from a specific symbol.
    Identify the 'Happy Path' and dependencies of an entry point.
    """
    request_id = new_request_id()
    is_valid_uuid, error_uuid = validate_uuid(start_symbol_id)
    if not is_valid_uuid:
        return _err(error_uuid, "VAL_003", request_id, status_code=422)

    is_valid_depth, error_depth = validate_max_depth(max_depth)
    if not is_valid_depth:
        return _err(error_depth, "VAL_004", request_id, status_code=422)

    orchestrator = create_orchestrator()
    db = orchestrator.db

    visited = set()

    async def trace(s_id, depth):
        if depth > max_depth or s_id in visited:
            return None
        visited.add(s_id)

        # Get symbol info and outgoing edges in a thread-safe way
        def _get_node_data():
            cursor = db.conn.execute("SELECT id, name, code, symbol_type FROM symbols WHERE id = ?", (s_id,))
            row = cursor.fetchone()
            if not row: return None, []

            cursor = db.conn.execute("""
                SELECT target_id FROM edges
                WHERE source_id = ? AND relation_type = 'CALLS'
            """, (s_id,))
            targets = [r['target_id'] for r in cursor.fetchall()]
            return dict(row), targets

        current_node, targets = await asyncio.to_thread(_get_node_data)
        if not current_node: return None
        
        current_node['calls'] = []
        for t_id in targets:
            child_flow = await trace(t_id, depth + 1)
            if child_flow:
                current_node['calls'].append(child_flow)

        return current_node

    result = await trace(start_symbol_id, 0)
    try:
        return _ok("Execution flow traced", {"flow": result, "depth_traced": max_depth}, request_id)
    finally:
        try:
            orchestrator.db.close()
        except Exception:
            pass

@mcp.tool()
async def index_codebase(path: str) -> Dict[str, Any]:
    """
    Index a codebase for semantic search and analysis.
    """
    request_id = new_request_id()
    is_valid, error_msg = validate_path(path)
    if not is_valid:
        return _err(error_msg, "VAL_101", request_id, status_code=422)

    orchestrator = create_orchestrator()
    try:
        repo_id = await orchestrator.repo_service.sync_repository(path)
        await orchestrator.index_service.index_repository(repo_id, request_id=request_id)
        
        def _get_counts():
            symbols_count = orchestrator.db.conn.execute(
                "SELECT COUNT(1) AS c FROM symbols WHERE repository_id = ?",
                (repo_id,),
            ).fetchone()["c"]
            edges_count = orchestrator.db.conn.execute(
                "SELECT COUNT(1) AS c FROM edges WHERE repository_id = ?",
                (repo_id,),
            ).fetchone()["c"]
            return int(symbols_count), int(edges_count)
            
        symbols_count, edges_count = await asyncio.to_thread(_get_counts)
        return _ok(
            "Indexing completed",
            {
                "repository_id": repo_id,
                "symbols_count": int(symbols_count),
                "edges_count": int(edges_count),
            },
            request_id,
        )
    except Exception as e:
        logger.exception("index_codebase failed")
        return _err(f"Indexing failed: {str(e)}", "SRV_101", request_id, status_code=500)
    finally:
        try:
            orchestrator.db.close()
        except Exception:
            pass

@mcp.tool()
async def get_structured_codemap(path: str) -> Dict[str, Any]:
    """
    Generate a high-density structured map of the codebase.
    Includes folders, files, and key symbols (classes/functions) for each file.
    """
    request_id = new_request_id()
    is_valid, error_msg = validate_path(path)
    if not is_valid:
        return _err(error_msg, "VAL_001", request_id, status_code=422)

    orchestrator = create_orchestrator()
    try:
        repo_id = orchestrator.get_repo_id(path)
        if not repo_id:
            return _err("Repository not indexed. Run index_codebase first.", "VAL_002", request_id, status_code=404)

        def _build_map():
            # Build a nested structure
            # 1. Get all directories
            dirs = orchestrator.db.conn.execute(
                "SELECT id, name, relative_path FROM directories WHERE repository_id = ? ORDER BY relative_path",
                (repo_id,)
            ).fetchall()

            # 2. Get all files
            files = orchestrator.db.conn.execute(
                "SELECT id, name, directory_id FROM files WHERE repository_id = ?",
                (repo_id,)
            ).fetchall()

            # 3. Get all key symbols
            symbols = orchestrator.db.conn.execute(
                "SELECT id, name, symbol_type, file_id FROM symbols WHERE repository_id = ? AND symbol_type IN ('class', 'function')",
                (repo_id,)
            ).fetchall()

            # Map construction
            tree = {}
            # Group symbols by file
            file_symbols = {}
            for s in symbols:
                f_id = s['file_id']
                if f_id not in file_symbols: file_symbols[f_id] = []
                file_symbols[f_id].append({"id": s['id'], "name": s['name'], "type": s['symbol_type']})

            # Group files by directory
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

        tree = await asyncio.to_thread(_build_map)

        return _ok("Structured codemap generated", {"codemap": tree}, request_id)
    except Exception as e:
        return _err(f"Codemap generation failed: {str(e)}", "SRV_004", request_id, status_code=500)
    finally:
        try:
            orchestrator.db.close()
        except Exception:
            pass

if __name__ == "__main__":
    import sys
    
    transport = os.getenv("CODECORTEX_TRANSPORT", "stdio").strip().lower()
    
    if transport in ("sse", "http"):
        # Launching the FastAPI wrapper (defined in http_server.py)
        # We import it here to avoid circular dependencies
        from src.http_server import main as run_server
        run_server()
    else:
        # Standard MCP Stdio transport
        mcp.run()
