"""
Tests for process detection (execution flow tracing).
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.domain.codegraph.core.knowledge_graph import (
    KnowledgeGraph, GraphNode, GraphRelationship, RelationshipType,
)
from src.domain.codegraph.application.process_detector import ProcessDetector


def _make_test_graph() -> KnowledgeGraph:
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="login", name="handleLogin", type="function", file_path="auth.py",
                          properties={"is_exported": True}))
    kg.add_node(GraphNode(id="validate", name="validateInput", type="function", file_path="auth.py"))
    kg.add_node(GraphNode(id="create_session", name="createSession", type="function", file_path="session.py"))
    kg.add_node(GraphNode(id="send_email", name="sendEmail", type="function", file_path="email.py"))
    kg.add_node(GraphNode(id="log", name="logActivity", type="function", file_path="log.py",
                          properties={"is_exported": False}))

    # CALLS edges: login -> validate -> create_session -> send_email
    kg.add_relationship(GraphRelationship(id="r1", source_id="login", target_id="validate", type=RelationshipType.CALLS))
    kg.add_relationship(GraphRelationship(id="r2", source_id="validate", target_id="create_session", type=RelationshipType.CALLS))
    kg.add_relationship(GraphRelationship(id="r3", source_id="create_session", target_id="send_email", type=RelationshipType.CALLS))
    kg.add_relationship(GraphRelationship(id="r4", source_id="log", target_id="send_email", type=RelationshipType.CALLS))
    return kg


def test_process_detection_finds_processes():
    kg = _make_test_graph()
    detector = ProcessDetector(kg)
    processes, steps = detector.detect()
    # handleLogin should be detected as entry point (exported, callees > 0)
    assert len(processes) > 0
    assert any("handleLogin" in p["label"] for p in processes)


def test_process_detection_trace_length():
    kg = _make_test_graph()
    detector = ProcessDetector(kg)
    processes, steps = detector.detect()
    for p in processes:
        assert p["step_count"] >= 2


def test_process_steps():
    kg = _make_test_graph()
    detector = ProcessDetector(kg)
    processes, steps = detector.detect()
    if processes:
        p = processes[0]
        p_steps = [s for s in steps if s["process_id"] == p["id"]]
        assert len(p_steps) == p["step_count"]
        for s in p_steps:
            assert s["step"] >= 1


def test_process_empty_graph():
    kg = KnowledgeGraph()
    detector = ProcessDetector(kg)
    processes, steps = detector.detect()
    assert processes == []
    assert steps == []


if __name__ == "__main__":
    test_process_detection_finds_processes()
    test_process_detection_trace_length()
    test_process_steps()
    test_process_empty_graph()
    print("All process detection tests passed.")
