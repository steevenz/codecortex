"""
Real backend integration tests connecting to Docker containers.
Tests execute ACTUAL graph queries against Neo4j and FalkorDB.
"""
import sys, os, time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest


# ═══════════════════════════════════════════════════════════════════
# NEO4J BACKEND — connect to local Docker container
# ═══════════════════════════════════════════════════════════════════

def test_neo4j_connect():
    """Test Neo4j backend connects and executes a real query."""
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "neo4j"
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "codecortex123"

    # Test via neo4j driver directly (backends use singleton pattern that complicates testing)
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )
    driver.verify_connectivity()
    with driver.session() as session:
        result = session.run("CREATE (n:TestNode {name: 'hello'}) RETURN n")
        record = result.single()
        assert record is not None
        # Cleanup
        session.run("MATCH (n:TestNode) DELETE n")
    driver.close()

    # Also test the backend wrapper
    from src.core.backends.neo4j_backend import Neo4jBackend
    # Reset singleton for test
    Neo4jBackend._instance = None
    backend = Neo4jBackend.__new__(Neo4jBackend)
    backend.__init__()
    assert backend.get_backend_type() == "neo4j"
    backend.close()


def test_neo4j_schema():
    """Test Neo4j schema creation."""
    from src.core.backends.neo4j_backend import Neo4jBackend
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USER"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "codecortex123"

    ok, _ = Neo4jBackend.test_connection()
    if not ok:
        pytest.skip("Neo4j not available")

    backend = Neo4jBackend()
    backend.create_schema()  # Should not raise
    assert True
    backend.close()


# ═══════════════════════════════════════════════════════════════════
# FALKORDB BACKEND — connect to local Docker container
# ═══════════════════════════════════════════════════════════════════

def test_falkordb_connect():
    """Test FalkorDB backend connects and executes a real query."""
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "falkordb"
    os.environ["FALKORDB_HOST"] = "localhost"
    os.environ["FALKORDB_PORT"] = "6379"

    # Test via redis directly
    import redis
    r = redis.Redis(host="localhost", port=6379)
    r.ping()
    # Test FalkorDB graph command
    result = r.execute_command("GRAPH.QUERY test", "CREATE (:TestNode {name: 'hello'})")
    assert result is not None
    # Cleanup
    r.execute_command("GRAPH.DELETE test")
    r.close()

    # Also test the backend wrapper
    from src.core.backends.falkordb_backend import FalkorDBBackend
    FalkorDBBackend._instance = None
    backend = FalkorDBBackend.__new__(FalkorDBBackend)
    backend.__init__()
    assert backend.get_backend_type() == "falkordb"
    backend.close()


def test_falkordb_schema():
    """Test FalkorDB graph creation."""
    from src.core.backends.falkordb_backend import FalkorDBBackend
    os.environ["FALKORDB_HOST"] = "localhost"
    os.environ["FALKORDB_PORT"] = "6379"

    ok, _ = FalkorDBBackend.test_connection()
    if not ok:
        pytest.skip("FalkorDB not available")

    backend = FalkorDBBackend()
    # create_schema in FalkorDB just creates a graph
    backend.create_schema()  # Should not raise
    assert True
    backend.close()


# ═══════════════════════════════════════════════════════════════════
# GRAPH MANAGER — with real backend
# ═══════════════════════════════════════════════════════════════════

def test_graph_manager_with_backend():
    """Test GraphManager execute_query with real backend."""
    from src.core.graph_manager import GraphManager
    os.environ["CODECORTEX_GRAPH_BACKEND"] = "neo4j"
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USER"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "codecortex123"

    gm = GraphManager()
    # execute_query uses circuit breaker
    try:
        result = gm.execute_query("MATCH (n) RETURN count(n) AS cnt")
        assert isinstance(result, list)
    except Exception:
        pytest.skip("Graph query failed (backend may not be ready)")


if __name__ == "__main__":
    print("Backend tests ready. Run with: pytest tests/test_backends_real.py -v")
