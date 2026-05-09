"""
Tests for in-memory Knowledge Graph.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.domain.codegraph.core.knowledge_graph import (
    KnowledgeGraph, GraphNode, GraphRelationship, RelationshipType,
)


def test_add_node():
    kg = KnowledgeGraph()
    node = GraphNode(id="n1", name="func_a", type="function", file_path="app.py")
    kg.add_node(node)
    assert kg.node_count == 1
    assert kg.get_node("n1") is node


def test_add_relationship():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    rel = GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS)
    kg.add_relationship(rel)
    assert kg.relationship_count == 1


def test_get_callees():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    kg.add_node(GraphNode(id="c", name="C", type="function"))
    kg.add_relationship(GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS))
    kg.add_relationship(GraphRelationship(id="r2", source_id="a", target_id="c", type=RelationshipType.CALLS))
    callees = kg.get_callees("a")
    assert "b" in callees
    assert "c" in callees


def test_get_callers():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    kg.add_relationship(GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS))
    callers = kg.get_callers("b")
    assert "a" in callers


def test_remove_node_with_edges():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    kg.add_relationship(GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS))
    kg.remove_node("a")
    assert kg.node_count == 1
    assert kg.relationship_count == 0


def test_remove_nodes_by_file():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="n1", name="f1", type="function", file_path="app.py"))
    kg.add_node(GraphNode(id="n2", name="f2", type="function", file_path="app.py"))
    kg.add_node(GraphNode(id="n3", name="f3", type="function", file_path="other.py"))
    removed = kg.remove_nodes_by_file("app.py")
    assert removed == 2
    assert kg.node_count == 1


def test_iter_relationships_by_type():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    kg.add_node(GraphNode(id="c", name="C", type="function"))
    kg.add_relationship(GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS))
    kg.add_relationship(GraphRelationship(id="r2", source_id="a", target_id="c", type=RelationshipType.IMPORTS))
    calls = list(kg.get_relationships_by_type(RelationshipType.CALLS))
    assert len(calls) == 1
    imports = list(kg.get_relationships_by_type(RelationshipType.IMPORTS))
    assert len(imports) == 1


def test_to_networkx():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    kg.add_relationship(GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS))
    nx_g = kg.to_networkx()
    assert nx_g.number_of_nodes() == 2
    assert nx_g.number_of_edges() == 1


def test_to_dict():
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="n1", name="test", type="function"))
    d = kg.to_dict()
    assert d["stats"]["nodes"] == 1
    assert len(d["nodes"]) == 1


if __name__ == "__main__":
    test_add_node()
    test_add_relationship()
    test_get_callees()
    test_get_callers()
    test_remove_node_with_edges()
    test_remove_nodes_by_file()
    test_iter_relationships_by_type()
    test_to_networkx()
    test_to_dict()
    print("All Knowledge Graph tests passed.")
