"""
Mixin for graph analysis, clustering, and heuristic scoring.

:project: CodeCortex
:package: Modules.Codegraph.Services.Mixins.Analysis
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import contextlib
import io
import inspect
import sys
from typing import Any, Dict, List

import networkx as nx


class ArchitecturalAnalysisMixin:
    """Mixin for graph analysis, clustering, and heuristic scoring."""

    def _suppress_output(self):
        return contextlib.redirect_stdout(io.StringIO())

    def cluster_communities(self, G: nx.Graph) -> Dict[int, List[str]]:
        """Run community detection. Returns {community_id: [node_ids]}."""
        if G.number_of_nodes() == 0:
            return {}
        if G.is_directed():
            G = G.to_undirected()
        
        # Leiden warns and drops isolates - handle them separately
        isolates = [n for n in G.nodes() if G.degree(n) == 0]
        connected_nodes = [n for n in G.nodes() if G.degree(n) > 0]
        connected = G.subgraph(connected_nodes)

        raw: Dict[int, List[str]] = {}
        if connected.number_of_nodes() > 0:
            partition = self._partition_graph(connected)
            for node, cid in partition.items():
                raw.setdefault(cid, []).append(node)

        # Each isolate becomes its own single-node community
        next_cid = max(raw.keys(), default=-1) + 1
        for node in isolates:
            raw[next_cid] = [node]
            next_cid += 1

        # Re-index by size descending for deterministic ordering
        final_communities = list(raw.values())
        final_communities.sort(key=len, reverse=True)
        return {i: sorted(nodes) for i, nodes in enumerate(final_communities)}

    def _partition_graph(self, G: nx.Graph) -> Dict[str, int]:
        """Tries Leiden first, falls back to Louvain."""
        try:
            from graspologic.partition import leiden
            old_stderr = sys.stderr
            try:
                sys.stderr = io.StringIO()
                with self._suppress_output():
                    result = leiden(G)
            finally:
                sys.stderr = old_stderr
            return result
        except ImportError:
            pass

        # Fallback: Louvain
        kwargs = {"seed": 42, "threshold": 1e-4}
        UG = G.to_undirected()
        if "max_level" in inspect.signature(nx.community.louvain_communities).parameters:
            kwargs["max_level"] = 10
        communities = nx.community.louvain_communities(UG, **kwargs)
        return {node: cid for cid, nodes in enumerate(communities) for node in nodes}

    def cohesion_score(self, G: nx.Graph, community_nodes: List[str]) -> float:
        n = len(community_nodes)
        if n <= 1:
            return 1.0
        subgraph = G.subgraph(community_nodes)
        actual = subgraph.number_of_edges()
        possible = n * (n - 1) / 2
        return round(actual / possible, 2) if possible > 0 else 0.0

    def _is_file_node(self, G: nx.Graph, node_id: str) -> bool:
        """
        Return True if this node is a file-level hub node (e.g. 'client', 'models')
        or an AST method stub (e.g. '.auth_flow()', '.__init__()').
        """
        attrs = G.nodes[node_id]
        label = attrs.get("label", "")
        if not label:
            return False
            
        # File-level hub: label matches the actual source filename
        source_file = attrs.get("source_file", "")
        if source_file:
            from pathlib import Path as _Path
            if label == _Path(source_file).name:
                return True
                
        # Method stub: AST extractor labels methods as '.method_name()'
        if label.startswith(".") and label.endswith("()"):
            return True
            
        # Module-level function stub: labeled 'function_name()' - only has a contains edge
        if label.endswith("()") and G.degree(node_id) <= 1:
            return True
        return False

    def find_god_nodes(self, G: nx.DiGraph, top_n: int = 10) -> List[Dict[str, Any]]:
        """Identify high-impact nodes with architectural ranking. Excludes structural noise."""
        if G.number_of_nodes() == 0:
            return []
            
        degrees = dict(G.degree())
        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())
        
        # Calculate centrality
        try:
            pagerank = nx.pagerank(G, weight='weight') if G.number_of_edges() > 0 else {}
        except Exception:
            pagerank = {node: 0.0 for node in G.nodes()}
        
        candidates = []
        for node in G.nodes():
            if self._is_file_node(G, node):
                continue
                
            candidates.append({
                "id": node,
                "label": G.nodes[node].get("label", node),
                "degree": degrees.get(node, 0),
                "in_degree": in_degrees.get(node, 0),
                "out_degree": out_degrees.get(node, 0),
                "pagerank": round(pagerank.get(node, 0.0), 4),
            })
            
        candidates.sort(key=lambda x: (x["pagerank"], x["degree"]), reverse=True)
        return candidates[:top_n]

    def calculate_surprise_score(self, G: nx.DiGraph, source: str, target: str, communities: Dict[str, int]) -> float:
        """Ported high-fidelity heuristic for surprising connections."""
        score = 0.0
        reasons: List[str] = []
        
        data = G.get_edge_data(source, target) or {}
        
        # 1. Confidence weight
        conf = data.get("confidence", "EXTRACTED")
        conf_bonus = {"AMBIGUOUS": 0.3, "INFERRED": 0.2, "EXTRACTED": 0.1}.get(conf, 0.1)
        score += conf_bonus
        
        # 2. Cross-community bonus
        src_cid = communities.get(source)
        tgt_cid = communities.get(target)
        if src_cid is not None and tgt_cid is not None and src_cid != tgt_cid:
            score += 0.5
            reasons.append("bridges separate communities")
            
        # 3. Hub-to-Peripheral bonus
        src_degree = G.degree(source)
        tgt_degree = G.degree(target)
        if min(src_degree, tgt_degree) <= 2 and max(src_degree, tgt_degree) >= 10:
            score += 0.4
            reasons.append("peripheral-hub link")
            
        return round(score, 2)

    def suggest_architectural_questions(self, G: nx.DiGraph, god_nodes: List[Dict], communities: Dict[int, List[str]] = None) -> List[str]:
        """Generate inquisitive prompts based on graph topology."""
        questions = []
        if not god_nodes:
            return ["Why is the codebase so disconnected? (No clear central hubs found)"]
            
        top_hub = god_nodes[0]["id"]
        questions.append(f"What is the single responsibility of {top_hub}? It appears to be a massive central hub.")
        
        # Bridge nodes
        if G.number_of_edges() > 0:
            try:
                betweenness = nx.betweenness_centrality(G, k=min(100, G.number_of_nodes()))
                bridges = sorted([(n, s) for n, s in betweenness.items() if not self._is_file_node(G, n) and s > 0], 
                                key=lambda x: x[1], reverse=True)[:2]
                for node_id, score in bridges:
                    label = G.nodes[node_id].get("label", node_id)
                    questions.append(f"Why is `{label}` such a critical structural bridge? Changes here may have cascading effects.")
            except Exception:
                pass

        # Isolated components
        if not nx.is_weakly_connected(G):
            components = list(nx.weakly_connected_components(G))
            if len(components) > 1:
                questions.append(f"The graph is split into {len(components)} isolated clusters. Is this intentional decoupling or a missing dependency link?")
                
        return questions

    def analyze_module_dependencies(self, repo_id: str) -> Dict[str, Any]:
        """
        Aggregate symbol-level edges into a module-level dependency map.
        Identifies 'Core' modules vs 'Peripheral' modules.
        """
        # 1. Fetch all edges with their symbol file info
        sql = """
            SELECT 
                d1.relative_path AS source_module,
                d2.relative_path AS target_module,
                COUNT(*) AS call_count,
                SUM(e.weight) AS total_weight
            FROM edges e
            JOIN symbols s1 ON e.source_id = s1.id
            JOIN files f1 ON s1.file_id = f1.id
            JOIN directories d1 ON f1.directory_id = d1.id
            JOIN symbols s2 ON e.target_id = s2.id
            JOIN files f2 ON s2.file_id = f2.id
            JOIN directories d2 ON f2.directory_id = d2.id
            WHERE e.repository_id = ? AND d1.id != d2.id
            GROUP BY d1.relative_path, d2.relative_path
            ORDER BY total_weight DESC
        """
        
        cursor = self.db.conn.execute(sql, (repo_id,))
        module_edges = [dict(row) for row in cursor.fetchall()]
        
        # 2. Identify top level modules
        modules = set()
        for e in module_edges:
            modules.add(e["source_module"])
            modules.add(e["target_module"])
            
        return {
            "module_count": len(modules),
            "dependencies": module_edges[:50],
            "summary": f"Detected {len(modules)} interacting modules with {len(module_edges)} cross-module links."
        }

    def analyze_hotspots(self, repo_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Identify 'hotspots' based on git commit frequency.
        Files with high change frequency often correlate with complexity or technical debt.
        """
        sql = """
            SELECT 
                d.relative_path || '/' || f.name as file_path,
                COUNT(fc.commit_id) as commit_count
            FROM file_commits fc
            JOIN files f ON fc.file_id = f.id
            JOIN directories d ON f.directory_id = d.id
            WHERE fc.repository_id = ?
            GROUP BY f.id
            ORDER BY commit_count DESC
            LIMIT ?
        """
        cursor = self.db.conn.execute(sql, (repo_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def analyze_temporal_coupling(self, repo_id: str, limit: int = 10, min_commits: int = 3) -> List[Dict[str, Any]]:
        """
        Identify 'temporal coupling' based on files frequently committed together.
        High co-commit counts between distinct modules may indicate hidden dependencies.
        """
        sql = """
            SELECT 
                d1.relative_path || '/' || f1.name as file_a,
                d2.relative_path || '/' || f2.name as file_b,
                COUNT(fc1.commit_id) as co_commits
            FROM file_commits fc1
            JOIN file_commits fc2 ON fc1.commit_id = fc2.commit_id AND fc1.file_id < fc2.file_id
            JOIN files f1 ON fc1.file_id = f1.id
            JOIN directories d1 ON f1.directory_id = d1.id
            JOIN files f2 ON fc2.file_id = f2.id
            JOIN directories d2 ON f2.directory_id = d2.id
            WHERE fc1.repository_id = ?
            GROUP BY f1.id, f2.id
            HAVING co_commits >= ?
            ORDER BY co_commits DESC
            LIMIT ?
        """
        cursor = self.db.conn.execute(sql, (repo_id, min_commits, limit))
        results = [dict(row) for row in cursor.fetchall()]
        
        if hasattr(self, "_log_event"):
            self._log_event("INFO", "TEMPORAL_COUPLING_ANALYZED", {
                "repository_id": repo_id,
                "pairs_found": len(results)
            })
            
        return results

    def find_stub_implementations(self, repo_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find stub implementations: functions/classes with only 'pass' or 'raise NotImplementedError'.
        These indicate incomplete work or placeholder code.
        """
        sql = """
            SELECT 
                s.name as symbol_name,
                s.symbol_type,
                d.relative_path || '/' || f.name as file_path,
                s.body
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            JOIN directories d ON f.directory_id = d.id
            WHERE s.repository_id = ?
              AND s.symbol_type IN ('function', 'class')
              AND (
                  (s.symbol_type = 'function' AND (s.body LIKE '%pass%' OR s.body LIKE '%NotImplementedError%')) OR
                  (s.symbol_type = 'class' AND s.body LIKE '%pass%')
              )
            LIMIT ?
        """
        cursor = self.db.conn.execute(sql, (repo_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def audit_codebase(self, repo_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        Comprehensive codebase audit combining multiple analysis dimensions.
        Returns findings for god nodes, security, dead code, complexity, and stubs.
        """
        G = self._build_graph_from_db_sync(repo_id)
        return {
            "god_nodes": self.find_god_nodes(G, top_n=min(limit, 10)),
            "security": self._audit_security_hygiene(repo_id),
            "dead_code": self.find_dead_code(repo_path=None, limit=limit),
            "complexity": self.find_most_complex_functions(limit=limit),
            "stubs": self.find_stub_implementations(repo_id, limit=limit),
        }

    def _build_graph_from_db_sync(self, repo_id: str) -> nx.DiGraph:
        """Synchronous version of _build_graph_from_db for internal use."""
        return self.graph_manager.get_graph(repo_id) or nx.DiGraph()
