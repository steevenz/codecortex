"""
/**
 * @project   CodeCortex
 * @package   CodeGraph/Analysis
 * @standard  Aegis-CrossStack-v1.0
 * * Process Detection — traces execution flows through the knowledge graph.
 *   Ported from GitNexus's process-processor.ts algorithm.
 *   Finds entry points, BFS-traces via CALLS edges, and deduplicates similar paths.
 */
"""

import logging
from typing import List, Dict, Set, Optional, Tuple
from collections import deque
from dataclasses import dataclass

from src.domain.codegraph.core.knowledge_graph import KnowledgeGraph, GraphNode, RelationshipType
from src.domain.codegraph.application.entry_point_scorer import EntryPointScorer, bulk_score_symbols

logger = logging.getLogger("CodeCortex.CodeGraph.ProcessDetector")

MAX_TRACE_DEPTH = 10
MAX_BRANCHING = 4
MAX_PROCESSES = 75
MIN_STEPS = 3


@dataclass
class ProcessNode:
    id: str
    label: str
    heuristic_label: str
    process_type: str  # 'intra_community' | 'cross_community'
    step_count: int
    communities: Set[str]
    entry_point_id: str
    trace: List[str]


@dataclass
class ProcessStep:
    node_id: str
    process_id: str
    step: int


class ProcessDetector:
    """
    Detects execution flows (processes) in the code graph.

    1. Scores and ranks entry points
    2. BFS-traces from each entry point via CALLS edges
    3. Deduplicates similar traces
    4. Labels with heuristic names
    """

    def __init__(self, graph: KnowledgeGraph, repo_root: Optional[str] = None):
        self.graph = graph
        self.scorer = EntryPointScorer(repo_root)

    def detect(self) -> Tuple[List[Dict], List[Dict]]:
        """Run process detection. Returns (processes, steps)."""
        symbols = self._collect_symbols()
        scored = bulk_score_symbols(symbols, repo_root=None)

        # Sort by score, take top as candidates
        entry_points = sorted(scored, key=lambda s: s.get("entry_score", 0), reverse=True)
        candidates = [ep for ep in entry_points if ep.get("entry_score", 0) >= 50][:MAX_PROCESSES]

        processes = []
        steps = []
        seen_traces: Set[str] = set()

        for ep in candidates:
            ep_id = ep.get("id", ep.get("name", ""))
            trace = self._bfs_trace(ep_id)

            if len(trace) < MIN_STEPS:
                continue

            # Deduplication: normalize trace path
            trace_key = "->".join(trace)
            if trace_key in seen_traces:
                continue
            seen_traces.add(trace_key)

            # Determine community info
            communities = self._get_communities(trace)
            process_type = "cross_community" if len(communities) > 1 else "intra_community"

            process_id = f"proc_{ep.get('name', 'unknown')}_{trace[-1][:8] if trace else 'end'}"
            heuristic_label = self._derive_label(trace)

            processes.append({
                "id": process_id,
                "label": f"{ep.get('name', '?')} → {heuristic_label}",
                "heuristic_label": heuristic_label,
                "process_type": process_type,
                "step_count": len(trace),
                "communities": list(communities),
                "entry_point_id": ep_id,
                "trace": trace,
            })

            for i, node_id in enumerate(trace):
                steps.append({
                    "node_id": node_id,
                    "process_id": process_id,
                    "step": i + 1,
                })

        return processes, steps

    def _collect_symbols(self) -> List[Dict]:
        symbols = []
        for node in self.graph.iter_nodes():
            if node.type in ("function", "method"):
                callees = self.graph.get_callees(node.id)
                callers = self.graph.get_callers(node.id)
                symbols.append({
                    "id": node.id,
                    "name": node.name,
                    "file_path": node.file_path,
                    "language": node.language or "python",
                    "callers_count": len(callers),
                    "callees_count": len(callees),
                    "is_exported": node.properties.get("is_exported", False),
                })
        return symbols

    def _bfs_trace(self, start_node_id: str) -> List[str]:
        """BFS trace from entry point forward via CALLS edges."""
        trace = [start_node_id]
        queue = deque([(start_node_id, 0)])
        visited: Set[str] = {start_node_id}

        while queue:
            current, depth = queue.popleft()
            if depth >= MAX_TRACE_DEPTH:
                continue

            callees = self.graph.get_callees(current)
            # Limit branching
            for callee in callees[:MAX_BRANCHING]:
                if callee not in visited:
                    visited.add(callee)
                    trace.append(callee)
                    queue.append((callee, depth + 1))

        return trace

    def _get_communities(self, node_ids: List[str]) -> Set[str]:
        """Extract community IDs from node properties."""
        communities: Set[str] = set()
        for nid in node_ids:
            node = self.graph.get_node(nid)
            if node and "community" in node.properties:
                communities.add(str(node.properties["community"]))
        return communities

    def _derive_label(self, trace: List[str]) -> str:
        """Derive a human-readable label from a trace path."""
        parts = []
        for i, nid in enumerate(trace):
            if i >= 3:
                break
            node = self.graph.get_node(nid)
            if node:
                parts.append(node.name)
            else:
                parts.append(nid[:12])
        return " → ".join(parts) if parts else "unknown_flow"
