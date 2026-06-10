"""
Community detection using Leiden algorithm (via python-igraph + leidenalg).
Falls back to Louvain (via NetworkX) if Leiden is unavailable.

:project: CodeCortex
:package: Modules.Codegraph.Core.Community_leiden
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import logging
from typing import List, Dict, Optional, Tuple
import networkx as nx
from networkx.algorithms.community import modularity

logger = logging.getLogger("CodeCortex.CodeGraph.Community")

try:
    import leidenalg as _la
    import igraph as _ig
    HAS_LEIDEN = True
    LEIDEN_BACKEND = "leidenalg"
except ImportError:
    HAS_LEIDEN = False
    LEIDEN_BACKEND = "louvain"

def detect_communities_leiden(
    graph: nx.Graph,
    resolution: float = 1.0,
    seed: int = 42
) -> Tuple[List[List[str]], float]:
    """
    Detect communities using Leiden algorithm (fallback to Louvain).

    Returns:
        communities: List of community node lists
        modularity_score: Modularity of the partition
    """
    if graph.number_of_nodes() == 0:
        return [], 0.0

    try:
        if LEIDEN_BACKEND == "leidenalg":
            ig_graph = _ig.Graph.TupleList(graph.edges(data=False), directed=False)
            partition = _la.find_partition(ig_graph, _la.ModularityVertexPartition, seed=seed)
            communities_list = []
            for p in partition:
                try:
                    communities_list.append([ig_graph.vs[n]["name"] for n in p])
                except Exception:
                    communities_list.append([str(ig_graph.vs[n].index) for n in p])
            community_sets = [set(c) for c in communities_list]
            mod_score = modularity(graph, community_sets)
            logger.info(f"Leiden: {len(communities_list)} communities (modularity: {mod_score:.4f})")
        else:
            from networkx.algorithms.community import louvain_communities
            communities = list(louvain_communities(graph, resolution=resolution, seed=seed))
            communities_list = [sorted(list(c)) for c in communities]
            mod_score = modularity(graph, communities)
            logger.info(f"Louvain: {len(communities_list)} communities (modularity: {mod_score:.4f})")

        return communities_list, mod_score
    except Exception as e:
        logger.error(f"Community detection failed: {e}")
        return [], 0.0

def build_nx_graph(
    edges: List[Dict],
    nodes: Optional[List[Dict]] = None
) -> nx.Graph:
    """Build NetworkX graph from edge list."""
    G = nx.Graph()
    for e in edges:
        src = e.get("source_id", e.get("source"))
        tgt = e.get("target_id", e.get("target"))
        weight = e.get("weight", 1.0)
        if src and tgt:
            G.add_edge(src, tgt, weight=weight)
    return G

def get_community_stats(
    communities: List[List[str]],
    total_nodes: int
) -> Dict:
    """Compute statistics about community structure."""
    sizes = [len(c) for c in communities]
    return {
        "total_communities": len(communities),
        "largest_community": max(sizes) if sizes else 0,
        "smallest_community": min(sizes) if sizes else 0,
        "avg_community_size": sum(sizes) / len(sizes) if sizes else 0,
        "coverage": sum(sizes) / total_nodes if total_nodes > 0 else 0,
    }
