"""
AEGIS Graph Audit – God Nodes & Architecture Smell Detection
Uses graph centrality metrics to detect god classes, modules, components, plugins, widgets, and services.
Inspired by Graphify and empirical analysis of large codebases.

:project: CodeCortex
:package: Modules.Codegraph.Services.Audit
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

import networkx as nx

from src.core.database import DatabaseManager
from src.core.graph import GraphManager
from src.core.logging import get_logger
from src.core import ApiError
from src.core.bridges.neocortex_client import NeocortexClient

logger = get_logger("CodeCortex.Domain.CodeGraph.GraphAudit")

class NodeType(str, Enum):
    CLASS = "class"
    MODULE = "module"
    COMPONENT = "component"
    PLUGIN = "plugin"
    WIDGET = "widget"
    SERVICE = "service"

@dataclass
class Issue:
    type: str
    message: str
    remediation: str

@dataclass
class GodNode:
    name: str
    type: str
    severity: str
    location: Dict[str, Any]
    metrics: Dict[str, Any]
    issues: List[Issue]
    thresholds_used: Dict[str, Any]

@dataclass
class CircularDependency:
    cycle: List[str]
    length: int
    severity: str
    remediation: str

@dataclass
class Suggestion:
    severity: str
    message: str
    affected_node: Optional[str] = None
    affected_cycle: Optional[str] = None

class AEGISGraphAudit:
    """
    Audit code graph for architecture smells and god nodes.
    Uses NetworkX for centrality calculations.
    """

    DEFAULT_THRESHOLDS = {
        "degree_threshold": 10,
        "in_degree_threshold": 5,
        "out_degree_threshold": 10,
        "lines_threshold": 300,
        "methods_threshold": 20,
        "complexity_threshold": 50,
        "max_depth": 5,
    }

    def __init__(self, db: DatabaseManager, graph_manager: Optional[GraphManager] = None):
        self.db = db
        self.graph_manager = graph_manager
        self._graph: Optional[nx.DiGraph] = None
        self._god_nodes: List[GodNode] = []
        self._circular_deps: List[CircularDependency] = []
        self._suggestions: List[Suggestion] = []
        self._thresholds: Dict[str, Any] = {}

    async def audit(
        self,
        repo_id: str,
        node_types: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        degree_threshold: int = 10,
        in_degree_threshold: int = 5,
        out_degree_threshold: int = 10,
        lines_threshold: int = 300,
        methods_threshold: int = 20,
        complexity_threshold: int = 50,
        max_depth: int = 5,
        include_suggestions: bool = True,
    ) -> Dict[str, Any]:
        start_time = datetime.now()

        self._thresholds = {
            "degree_threshold": degree_threshold,
            "in_degree_threshold": in_degree_threshold,
            "out_degree_threshold": out_degree_threshold,
            "lines_threshold": lines_threshold,
            "methods_threshold": methods_threshold,
            "complexity_threshold": complexity_threshold,
            "max_depth": max_depth,
        }

        if node_types is None:
            node_types = [NodeType.CLASS.value, NodeType.MODULE.value, NodeType.COMPONENT.value,
                          NodeType.PLUGIN.value, NodeType.WIDGET.value, NodeType.SERVICE.value]

        if metrics is None:
            metrics = ["degree", "in_degree", "out_degree", "betweenness", "pagerank"]

        repo_check = self.db.conn.execute(
            "SELECT id FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()
        if not repo_check:
            raise ApiError(f"Repository not found: {repo_id}", status_code=404, error_code="GRPH_009")

        self._graph = await self._load_graph(repo_id)
        if self._graph is None or self._graph.number_of_nodes() == 0:
            raise ApiError("Graph not built for repository. Run graph_build first.", status_code=409, error_code="GRPH_002")

        await self._detect_god_nodes(node_types, metrics, lines_threshold, methods_threshold, complexity_threshold)
        await self._detect_circular_dependencies(max_depth)
        if include_suggestions:
            self._generate_suggestions()

        result = self._build_output(repo_id, start_time)
        
        # Request executive summary from Neocortex Cognitive Engine
        try:
            neo_client = NeocortexClient.instance()
            problem_stmt = f"Analyze architecture audit for repository {repo_id}."
            context_str = json.dumps(result, default=str)[:4000]
            summary = await neo_client.request_executive_summary(problem_statement=problem_stmt, context=context_str)
            if summary:
                result["executive_summary"] = summary
        except Exception as e:
            logger.debug(f"[Neocortex Integration] Failed to fetch executive summary: {e}")

        return result

    async def _load_graph(self, repo_id: str) -> Optional[nx.DiGraph]:
        if self.graph_manager:
            backend = self.graph_manager.get_backend()
            session = backend.get_session()
            G = nx.DiGraph()
            try:
                for node in session.run("MATCH (n) RETURN n.node_id as id, n.name as name, n.type as type").data():
                    G.add_node(node["id"], name=node["name"], type=node["type"])
                for rel in session.run("MATCH (a)-[r]->(b) RETURN a.node_id as from, b.node_id as to, type(r) as rel").data():
                    G.add_edge(rel["from"], rel["to"], relation=rel["rel"])
                return G
            except Exception:
                return None
        return None

    async def _detect_god_nodes(
        self, node_types: List[str], metrics: List[str],
        lines_threshold: int, methods_threshold: int, complexity_threshold: int,
    ) -> None:
        if self._graph is None:
            return

        in_degree = nx.in_degree_centrality(self._graph)
        out_degree = nx.out_degree_centrality(self._graph)
        degree = nx.degree_centrality(self._graph)
        betweenness = nx.betweenness_centrality(self._graph)
        pagerank = nx.pagerank(self._graph)

        for node_id, attrs in self._graph.nodes(data=True):
            node_type = attrs.get("type", "unknown")
            if node_type not in node_types:
                continue

            in_d = in_degree.get(node_id, 0) * self._graph.number_of_nodes()
            out_d = out_degree.get(node_id, 0) * self._graph.number_of_nodes()
            deg = degree.get(node_id, 0) * self._graph.number_of_nodes()
            bt = betweenness.get(node_id, 0)
            pr = pagerank.get(node_id, 0)

            is_god = False
            issues = []

            if in_d > self._thresholds["in_degree_threshold"]:
                is_god = True
                issues.append(Issue(
                    type="high_inbound_dependency",
                    message=f"Node has {int(in_d)} inbound dependencies (threshold: {self._thresholds['in_degree_threshold']})",
                    remediation="Consider splitting into smaller modules or extracting interfaces"
                ))

            if out_d > self._thresholds["out_degree_threshold"]:
                is_god = True
                issues.append(Issue(
                    type="high_outbound_dependency",
                    message=f"Node has {int(out_d)} outbound dependencies (threshold: {self._thresholds['out_degree_threshold']})",
                    remediation="Apply dependency inversion or use service locator pattern"
                ))

            if node_type == NodeType.CLASS.value:
                loc = attrs.get("lines_of_code", 0)
                method_count = attrs.get("method_count", 0)
                ccx = attrs.get("cyclomatic_complexity", 0)

                if loc > lines_threshold:
                    is_god = True
                    issues.append(Issue(
                        type="too_many_lines",
                        message=f"Class has {loc} LOC (threshold: {lines_threshold})",
                        remediation="Extract classes by responsibility"
                    ))

                if method_count > methods_threshold:
                    is_god = True
                    issues.append(Issue(
                        type="too_many_methods",
                        message=f"Class has {method_count} methods (threshold: {methods_threshold})",
                        remediation="Split into smaller classes using Strategy or Facade pattern"
                    ))

                if ccx > complexity_threshold:
                    is_god = True
                    issues.append(Issue(
                        type="high_complexity",
                        message=f"Cyclomatic complexity {ccx} (threshold: {complexity_threshold})",
                        remediation="Extract conditional blocks into separate methods"
                    ))

            if node_type in (NodeType.MODULE.value, NodeType.PLUGIN.value, NodeType.WIDGET.value, NodeType.SERVICE.value):
                ccx = attrs.get("cyclomatic_complexity", 0)
                if ccx > complexity_threshold:
                    is_god = True
                    issues.append(Issue(
                        type="high_complexity",
                        message=f"Node has cyclomatic complexity {ccx} (threshold: {complexity_threshold})",
                        remediation="Refactor complex logic into smaller functions or classes"
                    ))

            if is_god:
                score = (
                    0.3 * deg +
                    0.2 * bt +
                    0.3 * pr +
                    0.2 * (min(in_d / self._thresholds["in_degree_threshold"], 2.0) / 2)
                )
                severity = "critical" if score > 0.7 else "high" if score > 0.5 else "medium" if score > 0.3 else "low"

                self._god_nodes.append(GodNode(
                    name=attrs.get("name", node_id),
                    type=node_type,
                    severity=severity,
                    location={"module": attrs.get("module", ""), "file": attrs.get("path", "")},
                    metrics={"lines_of_code": attrs.get("lines_of_code", 0), "method_count": attrs.get("method_count", 0), "cyclomatic_complexity": attrs.get("cyclomatic_complexity", 0), "in_degree": int(in_d), "out_degree": int(out_d), "betweenness_centrality": round(bt, 4), "pagerank": round(pr, 4)},
                    issues=issues,
                    thresholds_used=self._thresholds
                ))

        self._god_nodes.sort(key=lambda x: x.severity == "critical", reverse=True)

    async def _detect_circular_dependencies(self, max_depth: int) -> None:
        if self._graph is None:
            return

        try:
            cycles = list(nx.simple_cycles(self._graph))
            for cycle in cycles:
                if len(cycle) <= max_depth:
                    self._circular_deps.append(CircularDependency(
                        cycle=cycle,
                        length=len(cycle),
                        severity="high",
                        remediation="Break cycle using dependency inversion or event-driven communication"
                    ))
        except Exception:
            pass

    def _generate_suggestions(self) -> None:
        for god in self._god_nodes:
            if god.severity in ("critical", "high"):
                self._suggestions.append(Suggestion(
                    severity=god.severity,
                    message=f"{god.name} is a god {god.type}. Consider refactoring.",
                    affected_node=god.name
                ))

        for cd in self._circular_deps:
            self._suggestions.append(Suggestion(
                severity=cd.severity,
                message=f"Circular dependency detected: {' → '.join(cd.cycle)}",
                affected_cycle=' → '.join(cd.cycle)
            ))

    def _build_output(self, repo_id: str, start_time: datetime) -> Dict[str, Any]:
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        by_type = {}
        for god in self._god_nodes:
            key = f"god_{god.type}"
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "repo_id": repo_id,
            "audit_timestamp": end_time.isoformat(),
            "duration_ms": duration_ms,
            "summary": {
                "total_god_nodes": len(self._god_nodes),
                "by_type": by_type,
                "circular_dependencies_detected": len(self._circular_deps),
            },
            "god_nodes": [asdict(g) for g in self._god_nodes],
            "circular_dependencies": [asdict(cd) for cd in self._circular_deps],
            "thresholds_applied": self._thresholds,
            "suggestions": [asdict(s) for s in self._suggestions],
        }

    def _error_response(self, message: str, request_id: str) -> Dict[str, Any]:
        raise ApiError(message, status_code=400, error_code="GRPH_009")
