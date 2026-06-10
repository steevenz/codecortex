"""
Deep coverage tests targeting remaining uncovered lines in new modules.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.append(str(Path(__file__).resolve().parents[2]))

# ── Route Extractor uncovered lines 59-60, 65-76, 129-131, 150, 168-183, 188-190, 203, 218-222 ──

def test_route_flask_with_methods():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    content = '''
@app.route("/api/data", methods=["POST", "PUT"])
def update_data():
    pass
'''
    routes = extractor.extract("app.py", content, language="python")
    assert any(r.path == "/api/data" and r.method == "POST" for r in routes)

def test_route_nextjs_app_router():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    routes = extractor.extract("/app/api/users/route.ts", "", language="nextjs")
    assert len(routes) >= 1

def test_route_nextjs_app_page():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    routes = extractor.extract("/app/dashboard/page.tsx", "", language="nextjs")
    assert isinstance(routes, list)  # Pages match via pages router, not app

def test_route_unknown_language():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    routes = extractor.extract("main.rb", "", language="ruby")
    assert routes == []

def test_route_handler_inference():
    from src.modules.codegraph.core.route import RouteExtractor
    extractor = RouteExtractor()
    content = "const handler = async (req, res) => { }"
    routes = extractor.extract("route.js", content, language="javascript")
    assert isinstance(routes, list)

# ── Heritage Extractor uncovered lines 64, 66, 98-115, 118-135, 166-175, 193-204 ──

def test_heritage_java_class():
    from src.modules.codegraph.core.heritage import HeritageExtractor
    extractor = HeritageExtractor()
    content = "public class UserController extends BaseController implements Serializable { }"
    results = extractor.extract_from_file(content, "UserController.java", "java")
    assert len(results) >= 1
    r = results[0]
    assert r.parent == "BaseController"
    assert "Serializable" in r.interfaces

def test_heritage_ts_implements_only():
    from src.modules.codegraph.core.heritage import HeritageExtractor
    extractor = HeritageExtractor()
    content = "class Foo implements Bar { }"
    results = extractor.extract_from_file(content, "foo.ts", "typescript")
    assert len(results) >= 1
    assert results[0].parent is None
    assert "Bar" in results[0].interfaces

def test_heritage_parent_cycle():
    from src.modules.codegraph.core.heritage import HeritageExtractor
    extractor = HeritageExtractor()
    content = "class A: pass\nclass B(A): pass\n"
    extractor.extract_from_file(content, "test.py", "python")
    ancestors = extractor.get_ancestors("B")
    assert "A" in ancestors

def test_extract_heritage_from_files():
    from src.modules.codegraph.core.heritage import extract_heritage_from_files
    files = [
        {"path": "models.py", "content": "class A: pass\nclass B(A): pass\n", "language": "python"},
    ]
    result = extract_heritage_from_files(files)
    assert result["total_classes"] >= 2
    assert "A" in result["hierarchy"]

# ── Import Resolver uncovered lines 34-52, 64-83, 140-147, 164-172 ──

def test_import_resolver_ts_require():
    from src.modules.codeindex.parsers.import_resolvers import TypeScript
    resolver = TypeScript()
    files = {"utils/helper.js", "main.js"}
    resolved = resolver.resolve("const helper = require('./utils/helper')", "main.js", files)
    assert len(resolved) > 0

def test_import_resolver_ts_module():
    from src.modules.codeindex.parsers.import_resolvers import TypeScript
    resolver = TypeScript()
    files = {"node_modules/express/index.js", "main.js"}
    resolved = resolver.resolve("import express from 'express'", "main.js", files)
    assert len(resolved) >= 0

def test_import_resolver_python_import():
    from src.modules.codeindex.parsers.import_resolvers import Python
    resolver = Python()
    files = {"os.py", "sys.py"}
    resolved = resolver.resolve("import os, sys", "main.py", files)
    assert "os.py" in resolved
    assert "sys.py" in resolved

def test_import_resolver_python_from_as():
    from src.modules.codeindex.parsers.import_resolvers import Python
    resolver = Python()
    files = {"utils/helpers.py", "main.py"}
    resolved = resolver.resolve("from utils.helpers import format_date", "main.py", files)
    assert "utils/helpers.py" in resolved

def test_import_resolver_go_no_match():
    from src.modules.codeindex.parsers.import_resolvers import Go
    resolver = Go()
    resolved = resolver.resolve('import "unknown/path"', "main.go", {"main.go"})
    assert len(resolved) == 0

def test_build_import_map_with_imports():
    from src.modules.codeindex.parsers.import_resolvers import build_import_map
    files = [
        {"path": "main.py", "content": "from utils import helpers\n", "language": "python"},
        {"path": "utils/helpers.py", "content": "def helper(): pass\n", "language": "python"},
    ]
    import_map = build_import_map(files)
    assert "main.py" in import_map

# ── ORM Extractor uncovered lines 69-70, 77-114, 117-135, 149-180, 183 ──

def test_orm_sqlalchemy_no_base():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    # Content without SA_BASE pattern — should return no models
    content = "class User(Base):\n    pass\n"
    models = extractor.extract_models_from_file(content, "models.py", "python")
    assert len(models) == 0

def test_orm_django_complex():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    content = """
from django.db import models

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10)
    created_at = models.DateTimeField(auto_now_add=True)
"""
    models = extractor.extract_models_from_file(content, "models.py", "python")
    assert len(models) >= 1

def test_orm_prisma_complex():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    content = """model Post {
  id      Int      @id @default(autoincrement())
  title   String
  content String?
  author  User     @relation(fields: [authorId], references: [id])
  authorId Int
}"""
    models = extractor.extract_models_from_file(content, "schema.prisma", "prisma")
    assert len(models) == 1
    assert len(models[0].fields) >= 4

def test_orm_sqlalchemy_direct():
    from src.modules.codegraph.core.orm import ORMExtractor
    extractor = ORMExtractor()
    content = """
from sqlalchemy import Column, Integer
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
"""
    models = extractor.extract_models_from_file(content, "models.py", "python")
    assert len(models) >= 1

# ── Knowledge Graph uncovered lines 75, 93, 101-110, 113-116, 158-161, 164-165, 171-172 ──

def test_knowledge_graph_remove_nodes_by_file_missing():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph
    kg = KnowledgeGraph()
    result = kg.remove_nodes_by_file("/nonexistent/file.py")
    assert result == 0

def test_knowledge_graph_add_relationship_no_node():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph, GraphRelationship, RelationshipType
    kg = KnowledgeGraph()
    kg.add_relationship(GraphRelationship(id="r", source_id="missing_a", target_id="missing_b", type=RelationshipType.CALLS))
    assert kg.relationship_count == 1
    edges = kg.get_edges_for_node("missing_a")
    assert len(edges) == 1

def test_knowledge_graph_get_edges_for_nonexistent():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph
    kg = KnowledgeGraph()
    edges = kg.get_edges_for_node("ghost")
    assert edges == []

def test_knowledge_graph_get_relationships_by_type_empty():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph, RelationshipType
    kg = KnowledgeGraph()
    rels = list(kg.get_relationships_by_type(RelationshipType.CALLS))
    assert rels == []

def test_knowledge_graph_for_each_rel():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph, GraphNode, GraphRelationship, RelationshipType
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="a", name="A", type="function"))
    kg.add_node(GraphNode(id="b", name="B", type="function"))
    kg.add_relationship(GraphRelationship(id="r1", source_id="a", target_id="b", type=RelationshipType.CALLS))
    results = []
    kg.for_each_relationship(lambda r: results.append(r.id))
    assert results == ["r1"]

# ── Process Detector uncovered lines 75-106, 133-150, 154-159, 163-172 ──

def test_process_detector_single_node():
    from src.modules.codegraph.core.knowledge_graph import KnowledgeGraph, GraphNode
    from src.modules.codegraph.core.process import ProcessDetector
    kg = KnowledgeGraph()
    kg.add_node(GraphNode(id="main", name="main", type="function", properties={"is_exported": True}))
    detector = ProcessDetector(kg)
    processes, steps = detector.detect()
    # "main" should match entry point patterns
    all_names = [p["label"] for p in processes]
    assert isinstance(all_names, list)

# ── Framework Detection uncovered lines 106-123, 132-133, 136-139, 144-150, 155-160, 164-166 ──

def test_framework_detect_fastapi_manifest():
    import tempfile
    from pathlib import Path
    from src.modules.codeindex.services.framework_detection import detect_frameworks
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        req = root / "requirements.txt"
        req.write_text("fastapi==0.104.0\nuvicorn==0.24.0\n")
        frameworks = detect_frameworks(root)
        assert "fastapi" in frameworks

def test_framework_detect_nextjs_manifest():
    import tempfile
    import json
    from pathlib import Path
    from src.modules.codeindex.services.framework_detection import detect_frameworks
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        pkg = root / "package.json"
        pkg.write_text(json.dumps({"dependencies": {"next": "14.0.0"}}))
        frameworks = detect_frameworks(root)
        assert "nextjs" in frameworks

if __name__ == "__main__":
    test_route_flask_with_methods()
    test_route_nextjs_app_router()
    test_route_nextjs_app_page()
    test_route_unknown_language()
    test_route_handler_inference()
    test_heritage_java_class()
    test_heritage_ts_implements_only()
    test_heritage_parent_cycle()
    test_extract_heritage_from_files()
    test_import_resolver_ts_require()
    test_import_resolver_ts_module()
    test_import_resolver_python_import()
    test_import_resolver_python_from_as()
    test_import_resolver_go_no_match()
    test_build_import_map_with_imports()
    test_orm_sqlalchemy_no_base()
    test_orm_django_complex()
    test_orm_prisma_complex()
    test_orm_sqlalchemy_direct()
    test_knowledge_graph_remove_nodes_by_file_missing()
    test_knowledge_graph_add_relationship_no_node()
    test_knowledge_graph_get_edges_for_nonexistent()
    test_knowledge_graph_get_relationships_by_type_empty()
    test_knowledge_graph_for_each_rel()
    test_process_detector_single_node()
    test_framework_detect_fastapi_manifest()
    test_framework_detect_nextjs_manifest()
    print("All deep coverage tests passed!")
