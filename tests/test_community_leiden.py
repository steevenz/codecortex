"""
Tests for Leiden community detection.
"""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.append(str(Path(__file__).resolve().parents[1]))

import networkx as nx
from src.domain.codegraph.application.community_leiden import (
    detect_communities_leiden,
    build_nx_graph,
    get_community_stats,
    HAS_LEIDEN, LEIDEN_BACKEND,
)


def test_detect_communities_basic():
    G = nx.Graph()
    G.add_edge("a", "b", weight=1)
    G.add_edge("b", "c", weight=1)
    G.add_edge("d", "e", weight=1)
    communities, mod = detect_communities_leiden(G)
    assert len(communities) >= 2
    assert mod >= 0


def test_detect_communities_empty():
    communities, mod = detect_communities_leiden(nx.Graph())
    assert communities == []
    assert mod == 0.0


def test_build_nx_graph():
    edges = [
        {"source_id": "a", "target_id": "b", "weight": 1},
        {"source_id": "b", "target_id": "c", "weight": 2},
    ]
    G = build_nx_graph(edges)
    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 2
    assert G["a"]["b"]["weight"] == 1


def test_build_nx_graph_empty():
    G = build_nx_graph([])
    assert G.number_of_nodes() == 0


def test_get_community_stats():
    communities = [["a", "b"], ["c", "d", "e"]]
    stats = get_community_stats(communities, total_nodes=5)
    assert stats["total_communities"] == 2
    assert stats["largest_community"] == 3
    assert stats["smallest_community"] == 2
    assert stats["avg_community_size"] == 2.5
    assert stats["coverage"] == 1.0


def test_get_community_stats_empty():
    stats = get_community_stats([], total_nodes=0)
    assert stats["total_communities"] == 0
    assert stats["largest_community"] == 0
    assert stats["avg_community_size"] == 0


def test_detect_communities_single_node():
    G = nx.Graph()
    G.add_node("alone")
    communities, mod = detect_communities_leiden(G)
    # Single node without edges may return 0 communities (modularity fails)
    assert isinstance(communities, list)
    assert isinstance(mod, (int, float))


def test_detect_communities_dense():
    G = nx.complete_graph(10)
    communities, mod = detect_communities_leiden(G, resolution=0.5)
    assert len(communities) >= 1


if __name__ == "__main__":
    test_detect_communities_basic()
    test_detect_communities_empty()
    test_build_nx_graph()
    test_build_nx_graph_empty()
    test_get_community_stats()
    test_get_community_stats_empty()
    test_detect_communities_single_node()
    test_detect_communities_dense()
    print("All community Leiden tests passed.")
