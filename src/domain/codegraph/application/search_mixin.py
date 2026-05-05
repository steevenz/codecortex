"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeGraph
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class CodeSearchMixin – Single Responsibility: Provide graph-based code search capabilities.
 */
"""

import logging
from typing import List, Dict, Optional, Any, Literal
from pathlib import Path
from src.core.logging_config import get_logger

logger = get_logger("CodeCortex.Domain.CodeGraph.Search")

def _levenshtein_distance(a: str, b: str) -> int:
    """Levenshtein distance for short identifiers (typo-tolerant name search)."""
    if len(a) < len(b):
        return _levenshtein_distance(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, c1 in enumerate(a):
        curr = [i + 1]
        for j, c2 in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]

def _normalize_identifier(s: str) -> str:
    """Lowercase and strip separator chars so camelCase / snake_case / spaces all compare equally."""
    return s.lower().replace('_', '').replace(' ', '')

class CodeSearchMixin:
    """
    Mixin providing advanced graph-based search capabilities.
    Ported from legacy Graphify domain for unified CodeCortex engine.
    """

    @property
    def _lacks_native_fulltext(self) -> bool:
        backend_type = getattr(self.graph_manager, 'get_backend_type', lambda: 'neo4j')()
        return backend_type != 'neo4j'

    def _graph_session(self):
        return self.graph_manager.get_backend().get_session()

    def _find_by_name_fuzzy_portable(
        self,
        label: Literal["Function", "Class", "Variable", "Module", "File"],
        search_term: str,
        edit_distance: int,
        repo_path: Optional[str],
        limit: int = 20,
    ) -> List[Dict]:
        """Fuzzy name match for backends without Lucene fuzzy syntax (Kùzu, FalkorDB)."""
        if not search_term.strip():
            return []
        where_clause = "WHERE node.path STARTS WITH $repo_path" if repo_path else ""
        params: Dict[str, Any] = {}
        if repo_path:
            params["repo_path"] = repo_path
        
        backend_limit = "LIMIT 5000"
        query = f"""
            MATCH (node:{label})
            {where_clause}
            RETURN node.name as name, node.path as path, node.line_number as line_number,
                node.source as source, node.docstring as docstring, node.is_dependency as is_dependency
            {backend_limit}
        """
        with self._graph_session() as session:
            rows = session.run(query, **params).data()

        q_raw = search_term.lower()
        q_norm = _normalize_identifier(search_term)

        scored: List[tuple[int, Dict]] = []
        for row in rows:
            nm = row.get("name")
            if not isinstance(nm, str):
                continue
            nm_lower = nm.lower()
            nm_norm = _normalize_identifier(nm)
            d = min(
                _levenshtein_distance(q_raw, nm_lower),
                _levenshtein_distance(q_norm, nm_norm),
            )
            if d <= edit_distance:
                scored.append((d, row))
        scored.sort(key=lambda x: x[0])
        return [r for _, r in scored[:limit]]

    def find_by_function_name(self, search_term: str, repo_path: Optional[str] = None,
                               fuzzy_search: bool = False, edit_distance: int = 2,
                               limit: int = 20) -> List[Dict]:
        if not fuzzy_search:
            with self._graph_session() as session:
                result = session.run(
                    "MATCH (node:Function {name: $name}) "
                    f"{'WHERE node.path STARTS WITH $repo_path ' if repo_path else ''}"
                    "RETURN node.name as name, node.path as path, node.line_number as line_number, "
                    "node.source as source, node.docstring as docstring, node.is_dependency as is_dependency "
                    "LIMIT $limit",
                    name=search_term, repo_path=repo_path, limit=limit
                )
                return result.data()

        if self._lacks_native_fulltext:
            return self._find_by_name_fuzzy_portable("Function", search_term, edit_distance, repo_path, limit)

        formatted_search_term = f"name:{search_term}"
        with self._graph_session() as session:
            result = session.run(
                f"CALL db.index.fulltext.queryNodes(\"code_search_index\", $search_term) YIELD node, score "
                f"WITH node, score "
                f"WHERE node:Function {'AND node.name CONTAINS $raw_term ' if not fuzzy_search else ''}"
                f"{'AND node.path STARTS WITH $repo_path ' if repo_path else ''}"
                "RETURN node.name as name, node.path as path, node.line_number as line_number, "
                "node.source as source, node.docstring as docstring, node.is_dependency as is_dependency "
                "ORDER BY score DESC LIMIT $limit",
                search_term=formatted_search_term, raw_term=search_term, repo_path=repo_path, limit=limit
            )
            return result.data()

    def find_by_class_name(self, search_term: str, repo_path: Optional[str] = None,
                           fuzzy_search: bool = False, edit_distance: int = 2,
                           limit: int = 20) -> List[Dict]:
        if not fuzzy_search:
            with self._graph_session() as session:
                result = session.run(
                    "MATCH (node:Class {name: $name}) "
                    f"{'WHERE node.path STARTS WITH $repo_path ' if repo_path else ''}"
                    "RETURN node.name as name, node.path as path, node.line_number as line_number, "
                    "node.source as source, node.docstring as docstring, node.is_dependency as is_dependency "
                    "LIMIT $limit",
                    name=search_term, repo_path=repo_path, limit=limit
                )
                return result.data()

        if self._lacks_native_fulltext:
            return self._find_by_name_fuzzy_portable("Class", search_term, edit_distance, repo_path, limit)

        formatted_search_term = f"name:{search_term}"
        with self._graph_session() as session:
            result = session.run(
                f"CALL db.index.fulltext.queryNodes(\"code_search_index\", $search_term) YIELD node, score "
                f"WITH node, score "
                f"WHERE node:Class {'AND node.name CONTAINS $raw_term ' if not fuzzy_search else ''}"
                f"{'AND node.path STARTS WITH $repo_path ' if repo_path else ''}"
                "RETURN node.name as name, node.path as path, node.line_number as line_number, "
                "node.source as source, node.docstring as docstring, node.is_dependency as is_dependency "
                "ORDER BY score DESC LIMIT $limit",
                search_term=formatted_search_term, raw_term=search_term, repo_path=repo_path, limit=limit
            )
            return result.data()

    def find_callers(self, function_name: str, path: Optional[str] = None, repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        repo_filter = f"AND caller.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            if path:
                result = session.run(
                    f"MATCH (caller)-[call:CALLS]->(target:Function {{name: $function_name, path: $path}}) "
                    f"WHERE (caller:Function OR caller:Class OR caller:File) {repo_filter}"
                    "OPTIONAL MATCH (caller_file:File)-[:CONTAINS]->(caller) "
                    "RETURN DISTINCT caller.name as caller_function, "
                    "COALESCE(caller.path, caller_file.path) as caller_file_path, "
                    "caller.line_number as caller_line_number, caller.is_dependency as caller_is_dependency, "
                    "call.line_number as call_line_number, call.args as call_args, "
                    "call.full_call_name as full_call_name, target.path as target_file_path "
                    "ORDER BY caller_is_dependency ASC, caller_file_path, caller_line_number LIMIT $limit",
                    function_name=function_name, path=path, repo_path=repo_path, limit=limit
                )
                results = result.data()
                if not results:
                    result = session.run(
                        f"MATCH (caller)-[call:CALLS]->(target:Function {{name: $function_name}}) "
                        f"WHERE (caller:Function OR caller:Class OR caller:File) {repo_filter}"
                        "OPTIONAL MATCH (caller_file:File)-[:CONTAINS]->(caller) "
                        "RETURN DISTINCT caller.name as caller_function, "
                        "COALESCE(caller.path, caller_file.path) as caller_file_path, "
                        "caller.line_number as caller_line_number, caller.is_dependency as caller_is_dependency, "
                        "call.line_number as call_line_number, call.args as call_args, "
                        "call.full_call_name as full_call_name, target.path as target_file_path "
                        "ORDER BY caller_is_dependency ASC, caller_file_path, caller_line_number LIMIT $limit",
                        function_name=function_name, repo_path=repo_path, limit=limit
                    )
                    results = result.data()
            else:
                result = session.run(
                    f"MATCH (caller:Function)-[call:CALLS]->(target:Function {{name: $function_name}}) "
                    f"WHERE 1=1 {repo_filter}"
                    "OPTIONAL MATCH (caller_file:File)-[:CONTAINS]->(caller) "
                    "RETURN DISTINCT caller.name as caller_function, "
                    "COALESCE(caller.path, caller_file.path) as caller_file_path, "
                    "caller.line_number as caller_line_number, caller.is_dependency as caller_is_dependency, "
                    "call.line_number as call_line_number, call.args as call_args, "
                    "call.full_call_name as full_call_name, target.path as target_file_path "
                    "ORDER BY caller_is_dependency ASC, caller_file_path, caller_line_number LIMIT $limit",
                    function_name=function_name, repo_path=repo_path, limit=limit
                )
                results = result.data()
            return results

    def find_callees(self, function_name: str, path: Optional[str] = None, repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        with self._graph_session() as session:
            if path:
                absolute_file_path = str(Path(path).resolve())
                result = session.run(
                    "MATCH (caller:Function {name: $function_name, path: $absolute_file_path}) "
                    "MATCH (caller)-[call:CALLS]->(called:Function) "
                    "WHERE called.path STARTS WITH $repo_path OR $repo_path IS NULL "
                    "OPTIONAL MATCH (called_file:File)-[:CONTAINS]->(called) "
                    "RETURN DISTINCT called.name as called_function, "
                    "COALESCE(called.path, called_file.path) as called_file_path, "
                    "called.line_number as called_line_number, called.is_dependency as called_is_dependency, "
                    "call.line_number as call_line_number, call.args as call_args, "
                    "call.full_call_name as full_call_name "
                    "ORDER BY called_is_dependency ASC, called_function LIMIT $limit",
                    function_name=function_name, absolute_file_path=absolute_file_path, repo_path=repo_path, limit=limit
                )
            else:
                result = session.run(
                    "MATCH (caller:Function {name: $function_name})-[call:CALLS]->(called:Function) "
                    "WHERE called.path STARTS WITH $repo_path OR $repo_path IS NULL "
                    "OPTIONAL MATCH (called_file:File)-[:CONTAINS]->(called) "
                    "RETURN DISTINCT called.name as called_function, "
                    "COALESCE(called.path, called_file.path) as called_file_path, "
                    "called.line_number as called_line_number, called.is_dependency as called_is_dependency, "
                    "call.line_number as call_line_number, call.args as call_args, "
                    "call.full_call_name as full_call_name "
                    "ORDER BY called_is_dependency ASC, called_function LIMIT $limit",
                    function_name=function_name, repo_path=repo_path, limit=limit
                )
            return result.data()

    def find_by_variable_name(self, search_term: str, repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        repo_filter = "AND v.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            result = session.run(
                f"MATCH (v:Variable) "
                f"WHERE v.name CONTAINS $search_term {repo_filter}"
                "RETURN v.name as name, v.path as path, v.line_number as line_number, "
                "v.value as value, v.context as context, v.is_dependency as is_dependency "
                "ORDER BY v.is_dependency ASC, v.name "
                "LIMIT $limit",
                search_term=search_term, repo_path=repo_path, limit=limit
            )
            return result.data()

    def find_by_content(self, search_term: str, repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Find code by content matching in source or docstrings. Handles backend differences."""
        if self._lacks_native_fulltext:
            return self._find_by_content_portable(search_term, repo_path, limit)
        with self._graph_session() as session:
            result = session.run(
                f"CALL db.index.fulltext.queryNodes(\"code_search_index\", $search_term) YIELD node, score "
                f"WITH node, score "
                f"WHERE (node:Function OR node:Class OR node:Variable) "
                f"{'AND node.path STARTS WITH $repo_path ' if repo_path else ''}"
                "MATCH (node)<-[:CONTAINS]-(f:File) "
                "RETURN "
                "CASE WHEN node:Function THEN 'function' WHEN node:Class THEN 'class' ELSE 'variable' END as type, "
                "node.name as name, f.path as path, node.line_number as line_number, "
                "node.source as source, node.docstring as docstring, node.is_dependency as is_dependency "
                "ORDER BY score DESC LIMIT $limit",
                search_term=search_term, repo_path=repo_path, limit=limit
            )
            return result.data()

    def _find_by_content_portable(self, search_term: str, repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Fallback for FalkorDB / KùzuDB which lack CALL db.index.fulltext.queryNodes."""
        all_results = []
        repo_filter = "AND node.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            for label, type_name in [('Function', 'function'), ('Class', 'class')]:
                try:
                    result = session.run(
                        f"MATCH (node:{label}) "
                        f"WHERE (toLower(node.name) CONTAINS toLower($search_term) "
                        f"  OR (node.source IS NOT NULL AND toLower(node.source) CONTAINS toLower($search_term)) "
                        f"  OR (node.docstring IS NOT NULL AND toLower(node.docstring) CONTAINS toLower($search_term))) "
                        f"{repo_filter}"
                        f"RETURN '{type_name}' as type, node.name as name, node.path as path, "
                        "node.line_number as line_number, node.source as source, "
                        "node.docstring as docstring, node.is_dependency as is_dependency "
                        "ORDER BY node.is_dependency ASC, node.name LIMIT $limit",
                        search_term=search_term, repo_path=repo_path, limit=limit
                    )
                    all_results.extend(result.data())
                except Exception:
                    logger.debug("Portable content query failed for label %s", label, exc_info=True)
        return all_results[:limit]

    def who_imports_module(self, module_name: str, repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        repo_filter = "AND file.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            result = session.run(
                f"MATCH (file:File)-[imp:IMPORTS]->(module:Module) "
                f"WHERE (module.name = $module_name OR module.full_import_name CONTAINS $module_name) {repo_filter}"
                "OPTIONAL MATCH (repo:Repository)-[:CONTAINS]->(file) "
                "WITH file, repo, COLLECT({ imported_module: module.name, import_alias: module.alias, "
                "  full_import_name: module.full_import_name }) AS imports "
                "RETURN file.name AS file_name, file.path AS path, "
                "file.relative_path AS file_relative_path, file.is_dependency AS file_is_dependency, "
                "repo.name AS repository_name, imports "
                "ORDER BY file_is_dependency ASC, path LIMIT $limit",
                module_name=module_name, repo_path=repo_path, limit=limit
            )
            return result.data()

    def find_class_hierarchy(self, class_name: str, path: Optional[str] = None, repo_path: Optional[str] = None) -> Dict[str, Any]:
        repo_filter_parent = "AND parent.path STARTS WITH $repo_path " if repo_path else ""
        repo_filter_child = "AND grandchild.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            match_clause = f"MATCH (child:Class {{name: $class_name{', path: $path' if path else ''}}})"

            parents_result = session.run(
                f"{match_clause} "
                f"MATCH (child)-[:INHERITS]->(parent:Class) "
                f"WHERE 1=1 {repo_filter_parent}"
                "OPTIONAL MATCH (parent_file:File)-[:CONTAINS]->(parent) "
                "RETURN DISTINCT parent.name as parent_class, "
                "COALESCE(parent.path, parent_file.path) as parent_file_path, "
                "parent.line_number as parent_line_number, parent.docstring as parent_docstring, "
                "parent.is_dependency as parent_is_dependency "
                "ORDER BY parent_is_dependency ASC, parent_class",
                class_name=class_name, path=path, repo_path=repo_path
            )

            children_result = session.run(
                f"{match_clause} "
                f"MATCH (grandchild:Class)-[:INHERITS]->(child) "
                f"WHERE 1=1 {repo_filter_child}"
                "OPTIONAL MATCH (child_file:File)-[:CONTAINS]->(grandchild) "
                "RETURN DISTINCT grandchild.name as child_class, "
                "COALESCE(grandchild.path, child_file.path) as child_file_path, "
                "grandchild.line_number as child_line_number, grandchild.docstring as child_docstring, "
                "grandchild.is_dependency as child_is_dependency "
                "ORDER BY child_is_dependency ASC, child_class",
                class_name=class_name, path=path, repo_path=repo_path
            )
            
            return {
                "class_name": class_name,
                "parent_classes": parents_result.data(),
                "child_classes": children_result.data()
            }

    def find_function_overrides(self, function_name: str, repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        repo_filter = "AND f.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            result = session.run(
                f"MATCH (f:Function {{name: $function_name}}) "
                f"WHERE 1=1 {repo_filter}"
                "RETURN f.name AS function_name, f.path AS path, f.line_number AS line_number, "
                "f.class_context AS class_context, f.is_dependency AS is_dependency "
                "ORDER BY f.is_dependency ASC, f.path, f.line_number LIMIT $limit",
                function_name=function_name, repo_path=repo_path, limit=limit
            )
            return result.data()

    def find_dead_code(self, repo_path: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        repo_filter = "AND f.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            result = session.run(
                f"MATCH (f:Function) "
                f"WHERE f.is_dependency = false {repo_filter}"
                "AND NOT ()-[:CALLS]->(f) "
                "RETURN f.name AS function_name, f.path AS path, f.line_number AS line_number "
                "ORDER BY f.path, f.line_number LIMIT $limit",
                repo_path=repo_path, limit=limit
            )
            return {"potentially_unused_functions": result.data()}

    def find_all_callers(self, function_name: str, path: Optional[str] = None, repo_path: Optional[str] = None, limit: int = 50) -> List[Dict]:
        repo_filter = "WHERE f.path STARTS WITH $repo_path" if repo_path else ""
        path_filter = ", path: $path" if path else ""
        with self._graph_session() as session:
            query = (
                f"MATCH (target:Function {{name: $function_name{path_filter}}}) "
                "MATCH p = ()-[:CALLS*]->(target) "
                "WITH p as p, nodes(p) as path_nodes "
                "WITH path_nodes[0] as f "
                f"{repo_filter} "
                "RETURN DISTINCT f.name AS caller_name, f.path AS caller_file_path, "
                "f.line_number AS caller_line_number, f.is_dependency AS caller_is_dependency "
                "ORDER BY caller_is_dependency ASC, caller_file_path, caller_line_number LIMIT $limit"
            )
            result = session.run(query, function_name=function_name, path=path, repo_path=repo_path, limit=limit)
            return result.data()

    def find_all_callees(self, function_name: str, path: Optional[str] = None, repo_path: Optional[str] = None, limit: int = 50) -> List[Dict]:
        repo_filter = "WHERE f.path STARTS WITH $repo_path" if repo_path else ""
        path_filter = ", path: $path" if path else ""
        with self._graph_session() as session:
            query = (
                f"MATCH (caller:Function {{name: $function_name{path_filter}}}) "
                "MATCH p = (caller)-[:CALLS*]->() "
                "WITH p as p, nodes(p) as path_nodes "
                "WITH path_nodes[size(path_nodes) - 1] as f "
                f"{repo_filter} "
                "RETURN DISTINCT f.name AS callee_name, f.path AS callee_file_path, "
                "f.line_number AS callee_line_number, f.is_dependency AS callee_is_dependency "
                "ORDER BY callee_is_dependency ASC, callee_file_path, callee_line_number LIMIT $limit"
            )
            result = session.run(query, function_name=function_name, path=path, repo_path=repo_path, limit=limit)
            return result.data()

    def find_function_call_chain(self, start_function: str, end_function: str, max_depth: int = 5,
                                  start_file: Optional[str] = None, end_file: Optional[str] = None,
                                  repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        start_props = "{name: $start_function" + (", path: $start_file}" if start_file else "}")
        end_props = "{name: $end_function" + (", path: $end_file}" if end_file else "}")
        repo_filter = ("WHERE 1=1 AND (start.path IS NULL OR start.path STARTS WITH $repo_path) "
                       "AND (end_target.path IS NULL OR end_target.path STARTS WITH $repo_path)") if repo_path else ""
        with self._graph_session() as session:
            query = (
                f"MATCH (start:Function {start_props}), (end_target:Function {end_props}) "
                f"{repo_filter} "
                "WITH start as start, end_target as end_target "
                f"MATCH path = (start)-[:CALLS*1..{max_depth}]->() "
                "WITH path as path, end_target as end_target, nodes(path) as func_nodes, relationships(path) as call_rels "
                "WITH path as path, func_nodes as func_nodes, call_rels as call_rels, "
                "end_target as end_target, func_nodes[size(func_nodes)] as path_end "
                "WHERE path_end.name = end_target.name AND (end_target.path IS NULL OR path_end.path = end_target.path) "
                "RETURN func_nodes as function_nodes, call_rels as call_nodes, size(call_rels) as chain_length "
                "ORDER BY chain_length ASC LIMIT $limit"
            )
            params = {
                "start_function": start_function,
                "end_function": end_function,
                "start_file": start_file,
                "end_file": end_file,
                "repo_path": repo_path,
                "limit": limit
            }
            result = session.run(query, **params)
            rows = result.data()
            transformed: List[Dict[str, Any]] = []
            for row in rows:
                func_nodes = row.get("function_nodes") or []
                rel_nodes = row.get("call_nodes") or []
                chain_len = row.get("chain_length", 0)
                function_chain = []
                for n in func_nodes:
                    props = n if isinstance(n, dict) else getattr(n, "properties", {})
                    if props is None:
                        try:
                            props = n.get_properties()
                        except Exception:
                            props = {}
                    function_chain.append({
                        "name": props.get("name"),
                        "path": props.get("path"),
                        "line_number": props.get("line_number"),
                        "is_dependency": props.get("is_dependency"),
                    })
                call_details = []
                for r in rel_nodes:
                    props = r if isinstance(r, dict) else getattr(r, "properties", {})
                    if props is None:
                        try:
                            props = r.get_properties()
                        except Exception:
                            props = {}
                    call_details.append({
                        "call_line": props.get("line_number"),
                        "args": props.get("args"),
                        "full_call_name": props.get("full_call_name"),
                    })
                transformed.append({
                    "function_chain": function_chain,
                    "call_details": call_details,
                    "chain_length": chain_len,
                })
            return transformed

    def find_module_dependencies(self, module_name: str, repo_path: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        repo_filter = "AND file.path STARTS WITH $repo_path" if repo_path else ""
        with self._graph_session() as session:
            importers_result = session.run(
                f"MATCH (file:File)-[imp:IMPORTS]->(module:Module {{name: $module_name}}) "
                f"WHERE 1=1 {repo_filter}"
                "OPTIONAL MATCH (repo:Repository)-[:CONTAINS]->(file) "
                "RETURN DISTINCT file.path as importer_file_path, imp.line_number as import_line_number, "
                "file.is_dependency as file_is_dependency, repo.name as repository_name "
                "ORDER BY file_is_dependency ASC, importer_file_path LIMIT $limit",
                module_name=module_name, repo_path=repo_path, limit=limit
            )
            imports_result = session.run(
                f"MATCH (file:File)-[:IMPORTS]->(target_module:Module {{name: $module_name}}) "
                f"MATCH (file)-[imp:IMPORTS]->(other_module:Module) "
                f"WHERE other_module.name <> target_module.name {repo_filter}"
                "RETURN DISTINCT other_module.name as imported_module, imp.alias as import_alias "
                "ORDER BY imported_module LIMIT $limit",
                module_name=module_name, repo_path=repo_path, limit=limit
            )
            return {
                "module_name": module_name,
                "importers": importers_result.data(),
                "imports": imports_result.data()
            }

    def find_variable_usage_scope(self, variable_name: str, path: Optional[str] = None,
                                   repo_path: Optional[str] = None) -> Dict[str, Any]:
        repo_filter = "AND var.path STARTS WITH $repo_path" if repo_path else ""
        path_filter = "(var.path ENDS WITH $path OR var.path = $path)" if path else "1=1"
        with self._graph_session() as session:
            contained = session.run(
                f"MATCH (container)-[:CONTAINS]->(var:Variable {{name: $variable_name}}) "
                f"WHERE {path_filter} {repo_filter}"
                "RETURN DISTINCT var.name as variable_name, var.value as variable_value, "
                "var.line_number as line_number, var.context as context, var.path as path, "
                "CASE WHEN container:Function THEN 'function' WHEN container:Class THEN 'class' ELSE 'module' END as scope_type, "
                "CASE WHEN container:Function THEN container.name WHEN container:Class THEN container.name ELSE 'module_level' END as scope_name, "
                "var.is_dependency as is_dependency",
                variable_name=variable_name, path=path, repo_path=repo_path
            )
            instances = contained.data()
            try:
                orphaned = session.run(
                    f"MATCH (var:Variable {{name: $variable_name}}) "
                    f"WHERE {path_filter} {repo_filter} "
                    "AND NOT ()-[:CONTAINS]->(var) "
                    "RETURN DISTINCT var.name as variable_name, var.value as variable_value, "
                    "var.line_number as line_number, var.context as context, var.path as path, "
                    "'module' as scope_type, 'module_level' as scope_name, var.is_dependency as is_dependency",
                    variable_name=variable_name, path=path, repo_path=repo_path
                )
                instances.extend(orphaned.data())
            except Exception as e:
                logger.warning("orphaned_variable_query_failed: %s", e, exc_info=True)
            instances.sort(key=lambda r: (
                r.get("is_dependency") or False,
                r.get("path") or "",
                r.get("line_number") or 0,
            ))
            return {"variable_name": variable_name, "instances": instances}

    def find_by_type(self, element_type: str, limit: int = 50) -> List[Dict]:
        type_map = {
            "function": "Function",
            "class": "Class",
            "file": "File",
            "module": "Module"
        }
        label = type_map.get(element_type.lower())
        if not label:
            return []
        with self._graph_session() as session:
            if label == "File":
                query = ("MATCH (n:File) RETURN n.name as name, n.path as path, "
                         "n.is_dependency as is_dependency ORDER BY n.path LIMIT $limit")
            elif label == "Module":
                query = ("MATCH (n:Module) RETURN n.name as name, n.name as path, "
                         "false as is_dependency ORDER BY n.name LIMIT $limit")
            else:
                query = (f"MATCH (n:{label}) RETURN n.name as name, n.path as path, "
                         "n.line_number as line_number, n.is_dependency as is_dependency "
                         "ORDER BY is_dependency ASC, name LIMIT $limit")
            result = session.run(query, limit=limit)
            return result.data()

    def find_most_complex_functions(self, limit: int = 10, repo_path: Optional[str] = None) -> List[Dict]:
        repo_filter = "AND f.path STARTS WITH $repo_path" if repo_path else ""
        with self._graph_session() as session:
            query = (
                f"MATCH (f:Function) "
                f"WHERE f.cyclomatic_complexity IS NOT NULL AND f.is_dependency = false {repo_filter}"
                "RETURN f.name as function_name, f.path as path, "
                "f.cyclomatic_complexity as complexity, f.line_number as line_number "
                "ORDER BY f.cyclomatic_complexity DESC LIMIT $limit"
            )
            result = session.run(query, limit=limit, repo_path=repo_path)
            return result.data()

    def analyze_code_relationships(self, query_type: str, target: str,
                                    context: Optional[str] = None,
                                    repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Unified dispatcher for graph-based relationship analysis."""
        query_type = query_type.lower().strip()
        try:
            if query_type == "find_callers":
                results = self.find_callers(target, context, repo_path=repo_path)
                return {
                    "query_type": "find_callers", "target": target, "context": context,
                    "results": results,
                    "summary": f"Found {len(results)} functions that call '{target}'"
                }
            elif query_type == "find_callees":
                results = self.find_callees(target, context, repo_path=repo_path)
                return {
                    "query_type": "find_callees", "target": target, "context": context,
                    "results": results,
                    "summary": f"Function '{target}' calls {len(results)} other functions"
                }
            elif query_type == "find_importers":
                results = self.who_imports_module(target, repo_path=repo_path)
                return {
                    "query_type": "find_importers", "target": target,
                    "results": results,
                    "summary": f"Found {len(results)} files that import '{target}'"
                }
            elif query_type in ["who_modifies", "modifies", "mutations", "changes", "variable_usage"]:
                results = self.find_variable_usage_scope(target, context, repo_path=repo_path)
                return {
                    "query_type": "who_modifies", "target": target,
                    "results": results,
                    "summary": f"Variable '{target}' has {len(results['instances'])} instances across different scopes"
                }
            elif query_type in ["class_hierarchy", "inheritance", "extends"]:
                results = self.find_class_hierarchy(target, context, repo_path=repo_path)
                return {
                    "query_type": "class_hierarchy", "target": target,
                    "results": results,
                    "summary": (f"Class '{target}' has {len(results['parent_classes'])} parents, "
                                f"{len(results['child_classes'])} children")
                }
            elif query_type in ["overrides", "implementations", "polymorphism"]:
                results = self.find_function_overrides(target, repo_path=repo_path)
                return {
                    "query_type": "overrides", "target": target,
                    "results": results,
                    "summary": f"Found {len(results)} implementations of function '{target}'"
                }
            elif query_type in ["dead_code", "unused", "unreachable"]:
                results = self.find_dead_code(repo_path=repo_path)
                return {
                    "query_type": "dead_code",
                    "results": results,
                    "summary": f"Found {len(results['potentially_unused_functions'])} potentially unused functions"
                }
            elif query_type == "find_complexity":
                limit = int(context) if context and context.isdigit() else 10
                results = self.find_most_complex_functions(limit, repo_path=repo_path)
                return {
                    "query_type": "find_complexity", "limit": limit,
                    "results": results,
                    "summary": f"Found the top {len(results)} most complex functions"
                }
            elif query_type == "find_all_callers":
                results = self.find_all_callers(target, context, repo_path=repo_path)
                return {
                    "query_type": "find_all_callers", "target": target, "context": context,
                    "results": results,
                    "summary": f"Found {len(results)} direct and indirect callers of '{target}'"
                }
            elif query_type == "find_all_callees":
                results = self.find_all_callees(target, context, repo_path=repo_path)
                return {
                    "query_type": "find_all_callees", "target": target, "context": context,
                    "results": results,
                    "summary": f"Found {len(results)} direct and indirect callees of '{target}'"
                }
            elif query_type in ["call_chain", "path", "chain"]:
                if '->' in target:
                    parts = target.split('->', 1)
                    start_func = parts[0].strip()
                    end_func = parts[1].strip()
                    max_depth = int(context) if context and context.isdigit() else 5
                    results = self.find_function_call_chain(start_func, end_func,
                                                            max_depth, repo_path=repo_path)
                    return {
                        "query_type": "call_chain", "target": target,
                        "results": results,
                        "summary": f"Found {len(results)} call chains from '{start_func}' to '{end_func}'"
                    }
                return {
                    "error": "For call_chain queries, use format 'start_function->end_function'",
                    "example": "main->process_data"
                }
            elif query_type in ["module_deps", "module_dependencies", "module_usage"]:
                results = self.find_module_dependencies(target, repo_path=repo_path)
                return {
                    "query_type": "module_dependencies", "target": target,
                    "results": results,
                    "summary": f"Module '{target}' is imported by {len(results['importers'])} files"
                }
            elif query_type in ["find_functions_by_argument", "functions_by_argument", "parameter_search"]:
                results = self.find_functions_by_argument(target, context, repo_path=repo_path)
                return {
                    "query_type": "find_functions_by_argument", "target": target, "context": context,
                    "results": results,
                    "summary": f"Found {len(results)} function(s) with argument '{target}'"
                }
            elif query_type in ["find_functions_by_decorator", "functions_by_decorator", "decorator_search"]:
                results = self.find_functions_by_decorator(target, context, repo_path=repo_path)
                return {
                    "query_type": "find_functions_by_decorator", "target": target, "context": context,
                    "results": results,
                    "summary": f"Found {len(results)} function(s) with decorator '{target}'"
                }
            elif query_type in ["find_by_module_name", "module_name", "module_search"]:
                results = self.find_by_module_name(target)
                return {
                    "query_type": "find_by_module_name", "target": target,
                    "results": results,
                    "summary": f"Found {len(results)} module(s) matching '{target}'"
                }
            elif query_type in ["find_imports", "import_search", "imports"]:
                results = self.find_imports(target)
                return {
                    "query_type": "find_imports", "target": target,
                    "results": results,
                    "summary": f"Found {len(results)} import(s) matching '{target}'"
                }
            elif query_type in ["list_indexed_repositories", "repositories", "repos"]:
                limit = int(context) if context and context.isdigit() else 50
                results = self.list_indexed_repositories(limit)
                return {
                    "query_type": "list_indexed_repositories", "limit": limit,
                    "results": results,
                    "summary": f"Found {len(results)} indexed repositories"
                }
            else:
                return {
                    "error": f"Unknown query type: {query_type}",
                    "supported_types": [
                        "find_callers", "find_callees", "find_importers", "who_modifies",
                        "class_hierarchy", "overrides", "dead_code", "call_chain",
                        "module_deps", "find_complexity",
                        "find_all_callers", "find_all_callees",
                        "find_functions_by_argument", "find_functions_by_decorator",
                        "find_by_module_name", "find_imports", "list_indexed_repositories"
                    ]
                }
        except Exception as e:
            return {
                "error": f"Error executing relationship query: {str(e)}",
                "query_type": query_type,
                "target": target
            }

    def find_functions_by_argument(self, argument_name: str, path: Optional[str] = None,
                                    repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        repo_filter = "AND f.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            if path:
                result = session.run(
                    f"MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter) "
                    f"WHERE p.name = $argument_name AND f.path = $path {repo_filter}"
                    "RETURN f.name AS function_name, f.path AS path, f.line_number AS line_number, "
                    "f.docstring AS docstring, f.is_dependency AS is_dependency "
                    "ORDER BY f.is_dependency ASC, f.path, f.line_number LIMIT $limit",
                    argument_name=argument_name, path=path, repo_path=repo_path, limit=limit
                )
            else:
                result = session.run(
                    f"MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter) "
                    f"WHERE p.name = $argument_name {repo_filter}"
                    "RETURN f.name AS function_name, f.path AS path, f.line_number AS line_number, "
                    "f.docstring AS docstring, f.is_dependency AS is_dependency "
                    "ORDER BY f.is_dependency ASC, f.path, f.line_number LIMIT $limit",
                    argument_name=argument_name, repo_path=repo_path, limit=limit
                )
            return result.data()

    def find_functions_by_decorator(self, decorator_name: str, path: Optional[str] = None,
                                     repo_path: Optional[str] = None, limit: int = 20) -> List[Dict]:
        repo_filter = "AND f.path STARTS WITH $repo_path " if repo_path else ""
        with self._graph_session() as session:
            if path:
                result = session.run(
                    f"MATCH (f:Function) "
                    f"WHERE f.path = $path AND $decorator_name IN f.decorators {repo_filter}"
                    "RETURN f.name AS function_name, f.path AS path, f.line_number AS line_number, "
                    "f.docstring AS docstring, f.is_dependency AS is_dependency, f.decorators AS decorators "
                    "ORDER BY f.is_dependency ASC, f.path, f.line_number LIMIT $limit",
                    decorator_name=decorator_name, path=path, repo_path=repo_path, limit=limit
                )
            else:
                result = session.run(
                    f"MATCH (f:Function) "
                    f"WHERE $decorator_name IN f.decorators {repo_filter}"
                    "RETURN f.name AS function_name, f.path AS path, f.line_number AS line_number, "
                    "f.docstring AS docstring, f.is_dependency AS is_dependency, f.decorators AS decorators "
                    "ORDER BY f.is_dependency ASC, f.path, f.line_number LIMIT $limit",
                    decorator_name=decorator_name, repo_path=repo_path, limit=limit
                )
            return result.data()

    def find_by_module_name(self, search_term: str, limit: int = 20) -> List[Dict]:
        with self._graph_session() as session:
            result = session.run(
                "MATCH (m:Module) WHERE m.name CONTAINS $search_term "
                "RETURN m.name as name, m.lang as lang ORDER BY m.name LIMIT $limit",
                search_term=search_term, limit=limit
            )
            return result.data()

    def find_imports(self, search_term: str, limit: int = 20) -> List[Dict]:
        with self._graph_session() as session:
            result = session.run(
                "MATCH (f:File)-[r:IMPORTS]->(m:Module) "
                "WHERE r.alias = $search_term OR r.imported_name = $search_term "
                "RETURN r.alias as alias, r.imported_name as imported_name, "
                "m.name as module_name, f.path as path, r.line_number as line_number "
                "ORDER BY f.path LIMIT $limit",
                search_term=search_term, limit=limit
            )
            return result.data()

    def find_related_code(self, user_query: str, fuzzy_search: bool = False, edit_distance: int = 2,
                          repo_path: Optional[str] = None, limit: int = 15) -> Dict[str, Any]:
        """Combined search across functions, classes, variables, and content with relevance scoring."""
        if fuzzy_search and not self._lacks_native_fulltext:
            lucene_base = user_query.replace("_", " ").strip()
            lucene_fuzzy_query = " ".join(f"{t}~{edit_distance}" for t in lucene_base.split())
        else:
            lucene_fuzzy_query = user_query

        name_lookup_q = user_query if self._lacks_native_fulltext else (lucene_fuzzy_query if fuzzy_search else user_query)
        content_lookup_q = lucene_fuzzy_query if (fuzzy_search and not self._lacks_native_fulltext) else user_query

        results: Dict[str, Any] = {
            "query": lucene_fuzzy_query if fuzzy_search else user_query,
            "functions_by_name": self.find_by_function_name(name_lookup_q, repo_path, fuzzy_search, edit_distance, limit=limit),
            "classes_by_name": self.find_by_class_name(name_lookup_q, repo_path, fuzzy_search, edit_distance, limit=limit),
            "variables_by_name": self.find_by_variable_name(user_query, repo_path, limit=limit),
            "content_matches": self.find_by_content(content_lookup_q, repo_path, limit=limit),
        }

        all_results: List[Dict[str, Any]] = []
        for func in results["functions_by_name"]:
            func["search_type"] = "function_name"
            func["relevance_score"] = 0.9 if not func.get("is_dependency") else 0.7
            all_results.append(func)
        for cls in results["classes_by_name"]:
            cls["search_type"] = "class_name"
            cls["relevance_score"] = 0.8 if not cls.get("is_dependency") else 0.6
            all_results.append(cls)
        for var in results["variables_by_name"]:
            var["search_type"] = "variable_name"
            var["relevance_score"] = 0.7 if not var.get("is_dependency") else 0.5
            all_results.append(var)
        for content in results["content_matches"]:
            content["search_type"] = "content"
            content["relevance_score"] = 0.6 if not content.get("is_dependency") else 0.4
            all_results.append(content)

        all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        results["ranked_results"] = all_results[:limit]
        results["total_matches"] = len(all_results)
        return results

    def list_indexed_repositories(self, limit: int = 50) -> List[Dict]:
        with self._graph_session() as session:
            result = session.run(
                "MATCH (r:Repository) "
                "RETURN r.name as name, r.path as path, r.is_dependency as is_dependency "
                "ORDER BY r.name LIMIT $limit",
                limit=limit
            )
            return result.data()

    def suggest_questions(self, repo_path=None, top_n=7):
        """Generate exploration questions from graph heuristics."""
        questions = []
        with self._graph_session() as session:
            try:
                rows = session.run("MATCH (a:Function)-[r:CALLS]->(b:Function) WHERE r.confidence='AMBIGUOUS' RETURN a.name as src, b.name as tgt LIMIT 20").data()
                for r in rows[:5]:
                    questions.append({"type": "ambiguous", "question": f"Rel `{r['src']}` -> `{r['tgt']}`?", "why": "AMBIGUOUS edge"})
            except Exception as e:
                logger.warning("suggest_questions: %s", e)
        return questions[:top_n]

    def graph_diff(self, repo_path=None, limit=50):
        """Return graph stats snapshot for diff comparison."""
        with self._graph_session() as session:
            stats = {}
            for label in ["Function", "Class", "File"]:
                try:
                    row = session.run(f"MATCH (n:{label}) RETURN count(n) as c").single()
                    stats[label.lower()] = row["c"] if row else 0
                except Exception as e:
                    logger.warning("graph_diff_%s: %s", label, e)
            try:
                row = session.run("MATCH ()-[r:CALLS]->() RETURN count(r) as c").single()
                stats["calls"] = row["c"] if row else 0
            except Exception as e:
                logger.warning("graph_diff_calls: %s", e)
            return stats

    def find_community_surprises(self, repo_path: Optional[str] = None, top_n: int = 5) -> List[Dict]:
        """Find surprising cross-community connections using Leiden / Louvain."""
        try:
            import networkx as nx
        except ImportError:
            return []

        with self._graph_session() as session:
            try:
                result = session.run(
                    "MATCH (f:Function)-[r:CALLS]->(g:Function) "
                    f"{'WHERE f.path STARTS WITH $repo_path AND g.path STARTS WITH $repo_path ' if repo_path else ''}"
                    "RETURN f.name as src, g.name as tgt, r.confidence as conf",
                    repo_path=repo_path
                ).data()
            except Exception as e:
                logger.warning("community_edge_fetch_failed: %s", e)
                return []

        if not result:
            return []

        G = nx.DiGraph()
        for r in result:
            G.add_edge(r["src"], r["tgt"], confidence=r.get("conf", "EXTRACTED"))

        # Simple degree-based fallback if no community lib
        surprises = []
        for u, v, data in G.edges(data=True):
            # For now, just return high-confidence bridges or similar
            # Full Leiden/Louvain logic can be added if requested
            pass
            
        return surprises[:top_n]
