"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeGraph
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Module tools – Single Responsibility: Register and handle MCP tools for codegraph domain.
 */
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from src.domain.codegraph.application.service import CodeGraphService
from src.domain.codegraph.core.security import validate_url, validate_graph_path, sanitize_label

def register_tools(mcp: FastMCP, service: CodeGraphService) -> None:
    """
    Register all codegraph-related tools to the FastMCP instance.

    @param mcp: FastMCP server instance
    @param service: CodeGraphService instance to delegate work to
    """

    # -------------------------------------------------------------------------
    # Graph Construction Tools
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def map_relationships(repo_id: str) -> str:
        """
        DEPRECATED: Use build_repository_graph instead.
        Delegates to full AST-based graph construction pipeline.

        @param repo_id: Repository UUID
        @return: Build statistics
        """
        try:
            stats = service.map_relationships(repo_id)
            return f"[DEPRECATED map_relationships -> build_repository_graph] Graph built: {stats}"
        except Exception as e:
            return f"Error mapping relationships: {str(e)}"

    @mcp.tool()
    async def build_repository_graph(repo_id: str, repo_path: str) -> str:
        """
        Build full repository graph using Tree-sitter parsing and resolution.
        
        @param repo_id: Repository UUID
        @param repo_path: Repository root path
        @return: Build statistics
        """
        try:
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                return f"Repository path does not exist: {repo_path}"
            
            # Get all code files from database
            cursor = service.db.conn.execute("SELECT id, name, directory_id FROM files WHERE repository_id = ?", (repo_id,))
            files = cursor.fetchall()
            file_paths = []
            for f in files:
                dir_cursor = service.db.conn.execute("SELECT relative_path FROM directories WHERE id = ?", (f['directory_id'],))
                dir_row = dir_cursor.fetchone()
                if dir_row:
                    dir_path = dir_row['relative_path'] or ""
                    file_rel = f"{dir_path}/{f['name']}" if dir_path else f['name']
                    file_paths.append(repo_path_obj / file_rel)
            
            stats = service.build_repository_graph(repo_id, repo_path_obj, file_paths)
            return f"Graph built successfully: {stats}"
        except Exception as e:
            return f"Error building graph: {str(e)}"

    @mcp.tool()
    async def get_graph_stats(repo_id: str) -> str:
        """
        Get statistics from the graph backend.
        
        @param repo_id: Repository UUID
        @return: Graph statistics
        """
        try:
            backend = service.graph_manager.get_backend()
            with backend.get_session() as session:
                repo_row = service.db.conn.execute(
                    "SELECT root_path FROM repositories WHERE id = ?", (repo_id,)
                ).fetchone()
                repo_path = repo_row["root_path"] if repo_row else None

                if repo_path:
                    queries = {
                        "functions": ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(n:Function) RETURN count(n) AS count", {"p": repo_path}),
                        "classes":   ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(n:Class) RETURN count(n) AS count",    {"p": repo_path}),
                        "files":     ("MATCH (r:Repository {path:$p})-[:CONTAINS]->(n:File) RETURN count(n) AS count",           {"p": repo_path}),
                        "calls":     ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(a)-[e:CALLS]->() RETURN count(e) AS count", {"p": repo_path}),
                        "inherits":  ("MATCH (r:Repository {path:$p})-[:CONTAINS*1..2]->(a)-[e:INHERITS]->() RETURN count(e) AS count", {"p": repo_path}),
                    }
                else:
                    queries = {
                        "functions": ("MATCH (n:Function) RETURN count(n) AS count", {}),
                        "classes":   ("MATCH (n:Class) RETURN count(n) AS count", {}),
                        "files":     ("MATCH (n:File) RETURN count(n) AS count", {}),
                        "calls":     ("MATCH ()-[r:CALLS]->() RETURN count(r) AS count", {}),
                        "inherits":  ("MATCH ()-[r:INHERITS]->() RETURN count(r) AS count", {}),
                    }
                stats = {}
                for label, (q, params) in queries.items():
                    result = session.run(q, **params)
                    row = result.single()
                    stats[label] = row["count"] if row else 0
                return f"Graph stats for repo {repo_id}: {stats}"
        except Exception as e:
            return f"Error getting graph stats: {str(e)}"

    @mcp.tool()
    async def execute_cypher(query: str, repo_path: str) -> str:
        """Execute a raw Cypher query on the graph backend."""
        try:
            backend = service.graph_manager.get_backend()
            with backend.get_session() as session:
                result = session.run(query)
                try:
                    rows = result.data()
                except AttributeError:
                    rows = list(result)
                return f"Cypher query executed. Returned {len(rows)} rows."
        except Exception as e:
            return f"Error executing Cypher: {str(e)}"

    # -------------------------------------------------------------------------
    # Architectural Intelligence Tools
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def analyze_architecture(repo_id: str) -> str:
        """Run full architectural analysis (god nodes, surprising coupling, security)."""
        try:
            result = service.analyze_architecture(repo_id)
            return f"Architecture Analysis Results:\n\n{json.dumps(result, indent=2)}"
        except Exception as e:
            return f"Error analyzing architecture: {str(e)}"

    @mcp.tool()
    async def find_god_nodes(repo_id: str, threshold: int = 10) -> str:
        """Detect symbols with unusually high in-degree."""
        try:
            G = service._build_graph_from_db(repo_id)
            nodes = service.find_god_nodes(G, threshold)
            return f"God Nodes (threshold={threshold}):\n\n{json.dumps(nodes, indent=2)}"
        except Exception as e:
            return f"Error finding god nodes: {str(e)}"

    @mcp.tool()
    async def audit_security(repo_id: str) -> str:
        """Scan for sensitive patterns and security hygiene issues."""
        try:
            findings = service._audit_security_hygiene(repo_id)
            return f"Security Audit Results:\n\n{json.dumps(findings, indent=2)}"
        except Exception as e:
            return f"Error auditing security: {str(e)}"

    @mcp.tool()
    async def build_comprehensive_report(repo_id: str) -> str:
        """Generate a complete architectural health and complexity report."""
        try:
            report = service.build_comprehensive_report(repo_id)
            return f"Comprehensive Report:\n\n{json.dumps(report, indent=2)}"
        except Exception as e:
            return f"Error building report: {str(e)}"

    # -------------------------------------------------------------------------
    # Code Search & Discovery Tools (Graph-Based)
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def find_by_function_name(search_term: str, repo_path: Optional[str] = None,
                                     fuzzy_search: bool = False, edit_distance: int = 2,
                                     limit: int = 20) -> str:
        """Find functions by exact or fuzzy name matching."""
        try:
            results = service.find_by_function_name(search_term, repo_path, fuzzy_search, edit_distance, limit)
            return f"Found {len(results)} function(s):\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding functions: {str(e)}"

    @mcp.tool()
    async def find_callers(function_name: str, path: Optional[str] = None,
                          repo_path: Optional[str] = None, limit: int = 20) -> str:
        """Find what functions call a specific function."""
        try:
            results = service.find_callers(function_name, path, repo_path, limit)
            return f"Found {len(results)} caller(s):\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding callers: {str(e)}"

    @mcp.tool()
    async def find_callees(function_name: str, path: Optional[str] = None,
                          repo_path: Optional[str] = None, limit: int = 20) -> str:
        """Find what functions a specific function calls."""
        try:
            results = service.find_callees(function_name, path, repo_path, limit)
            return f"Found {len(results)} callee(s):\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding callees: {str(e)}"

    @mcp.tool()
    async def find_related_code(user_query: str, repo_path: Optional[str] = None, limit: int = 15) -> str:
        """Combined search across functions, classes, and variables with relevance scoring."""
        try:
            # CodeSearchMixin.find_related_code
            results = service.find_related_code(user_query, repo_path=repo_path, limit=limit)
            return f"Related code for '{user_query}':\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding related code: {str(e)}"

    @mcp.tool()
    async def find_by_class_name(search_term: str, repo_path: Optional[str] = None,
                                 fuzzy_search: bool = False, edit_distance: int = 2,
                                 limit: int = 20) -> str:
        """Find classes by exact or fuzzy name matching."""
        try:
            results = service.find_by_class_name(search_term, repo_path, fuzzy_search, edit_distance, limit)
            return f"Found {len(results)} class(es):\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding classes: {str(e)}"

    @mcp.tool()
    async def find_by_variable_name(search_term: str, repo_path: Optional[str] = None, limit: int = 20) -> str:
        """Find variables by name matching."""
        try:
            results = service.find_by_variable_name(search_term, repo_path, limit)
            return f"Found {len(results)} variable(s):\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding variables: {str(e)}"

    @mcp.tool()
    async def find_by_content(search_term: str, repo_path: Optional[str] = None, limit: int = 20) -> str:
        """Find code by content matching in source or docstrings."""
        try:
            results = service.find_by_content(search_term, repo_path, limit)
            return f"Found {len(results)} content match(es):\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding content: {str(e)}"

    @mcp.tool()
    async def who_imports_module(module_name: str, repo_path: Optional[str] = None, limit: int = 20) -> str:
        """Find which files import a specific module."""
        try:
            results = service.who_imports_module(module_name, repo_path, limit)
            return f"Found {len(results)} file(s) importing '{module_name}':\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding importers: {str(e)}"

    @mcp.tool()
    async def find_class_hierarchy(class_name: str, path: Optional[str] = None, repo_path: Optional[str] = None) -> str:
        """Get the parent and child classes for a given class."""
        try:
            results = service.find_class_hierarchy(class_name, path, repo_path)
            return f"Class Hierarchy for '{class_name}':\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding class hierarchy: {str(e)}"

    @mcp.tool()
    async def find_function_overrides(function_name: str, repo_path: Optional[str] = None, limit: int = 20) -> str:
        """Find all implementations/overrides of a function name across the graph."""
        try:
            results = service.find_function_overrides(function_name, repo_path, limit)
            return f"Found {len(results)} override(s) for '{function_name}':\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding overrides: {str(e)}"

    @mcp.tool()
    async def find_dead_code(repo_id: str, repo_path: Optional[str] = None, limit: int = 50) -> str:
        """Identify potentially unused functions (no inbound CALLS edges)."""
        try:
            results = service.find_dead_code(repo_path, limit)
            return f"Dead Code Analysis:\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding dead code: {str(e)}"

    @mcp.tool()
    async def analyze_code_relationships(query_type: str, target: str,
                                         context: Optional[str] = None,
                                         repo_path: Optional[str] = None) -> str:
        """
        Unified tool for deep relationship analysis.
        Supported types: find_callers, find_callees, find_importers, who_modifies, class_hierarchy, 
        overrides, dead_code, call_chain, module_deps, find_complexity, find_all_callers, find_all_callees.
        """
        try:
            results = service.analyze_code_relationships(query_type, target, context, repo_path)
            return f"Relationship Analysis ({query_type}):\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error analyzing relationships: {str(e)}"

    @mcp.tool()
    async def find_most_complex_functions(limit: int = 10, repo_path: Optional[str] = None) -> str:
        """List functions with the highest cyclomatic complexity."""
        try:
            results = service.find_most_complex_functions(limit, repo_path)
            return f"Top {limit} Complex Functions:\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error finding complex functions: {str(e)}"

    @mcp.tool()
    async def list_indexed_repositories(limit: int = 50) -> str:
        """List all repositories currently indexed in the graph backend."""
        try:
            results = service.list_indexed_repositories(limit)
            return f"Indexed Repositories:\n\n{json.dumps(results, indent=2)}"
        except Exception as e:
            return f"Error listing repositories: {str(e)}"

    # -------------------------------------------------------------------------
    # Security Utility Tools
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def validate_url_safe(url: str) -> str:
        """Validate a URL for SSRF safety."""
        try:
            validate_url(url)
            return f"URL '{url}' is safe."
        except ValueError as e:
            return f"Unsafe URL: {e}"

    @mcp.tool()
    async def sanitize_graph_label(text: str) -> str:
        """Sanitize a text label for graph node/edge labels."""
        return sanitize_label(text)
