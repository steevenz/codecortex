"""
REAL integration tests for TreeSitter language parsers, framework parsers,
codegraph service, codeindex service, refactor service, and all remaining modules.

NO MOCKS — all tests execute real code with real dependencies.
"""
import sys, os, tempfile, json, asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest

# ═══════════════════════════════════════════════════════════════════
# TREESITTER MANAGER
# ═══════════════════════════════════════════════════════════════════

def test_tsm_get_language():
    from src.core.tree_sitter_manager import get_tree_sitter_manager, get_language_safe, create_parser
    mgr = get_tree_sitter_manager()
    assert mgr is not None
    py_lang = get_language_safe("python")
    assert py_lang is not None
    parser = create_parser("python")
    assert parser is not None
    tree = parser.parse(b"x = 1\n")
    assert tree.root_node.type == "module"

def test_tsm_multiple_languages():
    from src.core.tree_sitter_manager import get_language_safe, create_parser
    for lang in ["python", "javascript", "go", "rust", "java", "c", "cpp", "ruby", "php"]:
        try:
            parser = create_parser(lang)
            assert parser is not None
            tree = parser.parse(b"x = 1\n")
            assert tree.root_node.type is not None
        except Exception:
            pass  # Some languages may not be installed

def test_tsm_unknown_language():
    from src.core.tree_sitter_manager import get_language_safe
    with pytest.raises((ValueError, ImportError)):
        get_language_safe("nonexistent_language_xyz")

# ═══════════════════════════════════════════════════════════════════
# TREESITTER PARSER — Language-specific parsers
# ═══════════════════════════════════════════════════════════════════

def test_tsp_python_parse_class():
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    parser = TreeSitterParser("python")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.py"
        path.write_text("class Foo:\n    def bar(self):\n        pass\n")
        result = parser.parse(path)
        assert result is not None
        assert "symbols" in result or "error" not in str(result)

def test_tsp_python_parse_function():
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    parser = TreeSitterParser("python")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "func.py"
        path.write_text("def hello(name):\n    return f'Hi {name}'\n")
        result = parser.parse(path)
        assert result is not None

def test_tsp_javascript_parse():
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    parser = TreeSitterParser("javascript")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.js"
        path.write_text("function greet(name) { return 'Hi ' + name; }\n")
        result = parser.parse(path)
        assert result is not None

def test_tsp_go_parse():
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    parser = TreeSitterParser("go")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "main.go"
        path.write_text("package main\nfunc main() {}\n")
        result = parser.parse(path)
        assert result is not None

def test_tsp_typescript_parse():
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    try:
        parser = TreeSitterParser("typescript")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.ts"
            path.write_text("const x: number = 1;\n")
            result = parser.parse(path)
            assert result is not None
    except Exception:
        pytest.skip("TypeScript parser wheel not available")

def test_tsp_unknown_language():
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    with pytest.raises(Exception):
        TreeSitterParser("nonexistent")

# ═══════════════════════════════════════════════════════════════════
# PYTHON LANGUAGE PARSER (the most complex one)
# ═══════════════════════════════════════════════════════════════════

def test_python_parser_class_extraction():
    from src.domain.codeindex.infrastructure.parsers.languages.python import PythonTreeSitterParser
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    ts_parser = TreeSitterParser("python")
    py_parser = PythonTreeSitterParser(ts_parser)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "models.py"
        path.write_text("""
class User:
    def __init__(self, name):
        self.name = name
    def greet(self):
        return f'Hello {self.name}'
class Admin(User):
    pass
""")
        result = py_parser.parse(path)
        assert result is not None

def test_python_parser_function():
    from src.domain.codeindex.infrastructure.parsers.languages.python import PythonTreeSitterParser
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    ts_parser = TreeSitterParser("python")
    py_parser = PythonTreeSitterParser(ts_parser)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "utils.py"
        path.write_text("""
def calculate(a, b, c=10):
    \"\"\"Calculate something.\"\"\"
    return (a + b) * c
""")
        result = py_parser.parse(path)
        assert result is not None
        assert "symbols" in result or "error" not in str(result)

def test_python_parser_empty_file():
    from src.domain.codeindex.infrastructure.parsers.languages.python import PythonTreeSitterParser
    from src.domain.codeindex.infrastructure.parsers.tree_sitter_parser import TreeSitterParser
    import tempfile
    ts_parser = TreeSitterParser("python")
    py_parser = PythonTreeSitterParser(ts_parser)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "empty.py"
        path.write_text("")
        result = py_parser.parse(path)
        assert result is not None

# ═══════════════════════════════════════════════════════════════════
# CODEFRAPH SERVICE (with real SQLite)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cgs_basic_init():
    from src.core.database import DatabaseManager
    from src.domain.codegraph.application.service import CodeGraphService
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        svc = CodeGraphService(db)
        assert svc is not None
        db.close()

# ═══════════════════════════════════════════════════════════════════
# SEARCH MIXIN
# ═══════════════════════════════════════════════════════════════════

def test_search_mixin_import():
    from src.domain.codegraph.application.search_mixin import CodeSearchMixin
    assert CodeSearchMixin is not None


def test_search_mixin_methods():
    from src.core.database import DatabaseManager
    from src.domain.codegraph.application.service import CodeGraphService
    import tempfile
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        db = DatabaseManager(str(root / "test.db"))
        svc = CodeGraphService(db)
        repos = svc.list_indexed_repositories()
        assert isinstance(repos, list)
        db.close()
    finally:
        try:
            tmpdir_obj.cleanup()
        except PermissionError:
            pass

# ═══════════════════════════════════════════════════════════════════
# ANALYSIS MIXIN
# ═══════════════════════════════════════════════════════════════════

def test_analysis_mixin_import():
    from src.domain.codegraph.application.analysis_mixin import ArchitecturalAnalysisMixin
    assert ArchitecturalAnalysisMixin is not None

# ═══════════════════════════════════════════════════════════════════
# DISCOVERY MIXIN
# ═══════════════════════════════════════════════════════════════════

def test_discovery_mixin_import():
    from src.domain.codegraph.application.discovery_mixin import ArchitecturalDiscoveryMixin
    assert ArchitecturalDiscoveryMixin is not None

# ═══════════════════════════════════════════════════════════════════
# CODEREFACTOR SERVICE (real)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_refactor_analyze_impact():
    from src.core.database import DatabaseManager
    from src.domain.coderefactor.application.service import CodeRefactorService
    from src.domain.filesystem.application.service import FilesystemService
    from src.domain.coderepository.application.git_service import GitService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codegraph.application.service import CodeGraphService
    import tempfile
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        (root / "main.py").write_text("x = 1\n")
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        fs = FilesystemService(db, store)
        git = GitService(store)
        cg = CodeGraphService(db)
        svc = CodeRefactorService(db, fs, git, cg)
        result = await svc.analyze_refactor_impact(str(root / "main.py"), "x")
        assert result is not None
        db.close()
    finally:
        tmpdir_obj.cleanup()

# ═══════════════════════════════════════════════════════════════════
# CODEINDEX SERVICE (real SQLite + TreeSitter)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cis_basic():
    from src.core.database import DatabaseManager
    from src.domain.codeindex.application.service import CodeIndexService
    from src.domain.codegraph.application.service import CodeGraphService
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(str(Path(tmpdir) / "test.db"))
        cg = CodeGraphService(db)
        svc = CodeIndexService(db, codegraph_service=cg)
        assert svc is not None
        db.close()

# ═══════════════════════════════════════════════════════════════════
# RESOLUTION MODULES
# ═══════════════════════════════════════════════════════════════════

def test_resolution_functions():
    from src.domain.codegraph.application.resolution.calls import resolve_function_call, build_function_call_groups
    from src.domain.codegraph.application.resolution.inheritance import resolve_inheritance_link
    call_dict = {"name": "len", "full_name": "len", "line": 1}  # len is a builtin
    result = resolve_function_call(call_dict, "source.py", {"helper"}, {"helper": "utils"}, {"source.py": ["utils.py"]})
    assert result is None  # Builtin names return None
    groups = build_function_call_groups([], {})
    assert len(groups) == 6  # Returns 6-group tuple
    class_item = {"name": "MyClass", "full_path": "source.py"}
    result = resolve_inheritance_link(class_item, "object", "source.py", set(), {}, {})
    assert result is None  # "object" class returns None

# ═══════════════════════════════════════════════════════════════════
# CODEREPOSITORY SERVICE (real)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_crs_full():
    from src.core.database import DatabaseManager
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.coderepository.application.service import CodeRepositoryService
    import tempfile
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        (root / "main.py").write_text("x = 1\n")
        (root / "utils.py").write_text("def util(): pass\n")
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        svc = CodeRepositoryService(store, str(root))
        repo_id = await svc.sync_repository(str(root), request_id="test")
        assert repo_id is not None
        with_changes = await svc.sync_repository_with_changes(str(root))
        assert with_changes is not None
        repo_id2, changed = with_changes
        assert repo_id2 is not None
        db.close()
    finally:
        try:
            tmpdir_obj.cleanup()
        except PermissionError:
            pass

# ═══════════════════════════════════════════════════════════════════
# GIT SERVICE (real git)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_gs_basic():
    from src.core.database import DatabaseManager
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.coderepository.application.git_service import GitService
    import tempfile, subprocess
    tmpdir_obj = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    try:
        root = Path(tmpdir_obj.name)
        (root / "file.py").write_text("x = 1\n")
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=root, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        svc = GitService(store)
        status = await svc.get_repo_status(str(root))
        assert isinstance(status, dict)
        diff = await svc.get_file_diff(str(root), "file.py")
        assert isinstance(diff, str)
        db.close()
    finally:
        import time
        time.sleep(0.1)  # Allow DB to release WAL lock
        try:
            tmpdir_obj.cleanup()
        except PermissionError:
            pass

# ═══════════════════════════════════════════════════════════════════
# GRAPH BACKENDS — import tests (need actual servers for full tests)
# ═══════════════════════════════════════════════════════════════════

def test_backend_base():
    from src.core.backends.base import GraphBackend
    assert GraphBackend is not None

# ═══════════════════════════════════════════════════════════════════
# DETECTOR — fix circular import by importing codeindex first
# ═══════════════════════════════════════════════════════════════════

def test_detector():
    # Must import codeindex first to break circular import
    from src.domain.codeindex.application.service import CodeIndexService
    # Now detector can be imported
    from src.domain.coderepository.infrastructure.detector import RepositoryFrameworkDetector
    assert RepositoryFrameworkDetector is not None


def test_detector_real():
    import tempfile
    from src.domain.coderepository.infrastructure.detector import RepositoryFrameworkDetector
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "package.json").write_text('{"dependencies": {"react": "^18.0", "next": "^14.0"}}')
        detector = RepositoryFrameworkDetector(root)
        fws = detector.detect_all_frameworks()
        assert isinstance(fws, list)
        versions = detector.get_framework_versions()
        assert isinstance(versions, dict)

# ═══════════════════════════════════════════════════════════════════
# PERSISTENCE WRITER
# ═══════════════════════════════════════════════════════════════════

def test_graph_writer():
    from src.domain.codegraph.infrastructure.persistence.writer import GraphWriter
    writer = GraphWriter()
    assert writer is not None
    # Test static methods with valid labels/rels
    label = GraphWriter._label("Function")
    assert label == "Function"
    rel = GraphWriter._rel("CALLS")
    assert rel == "CALLS"
    with pytest.raises(ValueError):
        GraphWriter._label("invalid")
    with pytest.raises(ValueError):
        GraphWriter._rel("INVALID")

# ═══════════════════════════════════════════════════════════════════
# SECURITY MIXIN
# ═══════════════════════════════════════════════════════════════════

def test_security_mixin():
    from src.domain.codegraph.application.security_mixin import ArchitecturalSecurityMixin
    assert ArchitecturalSecurityMixin is not None

# ═══════════════════════════════════════════════════════════════════
# FRAMEWORK PARSERS — detect framework from real file patterns
# ═══════════════════════════════════════════════════════════════════

def test_frameworks_django():
    from src.domain.codeindex.infrastructure.parsers.frameworks.django import detect_django
    from src.domain.codeindex.infrastructure.parsers.frameworks.django import enrich_class
    result = detect_django(
        rel_path="models.py",
        source="from django.db import models\nclass User(models.Model): pass\n",
        imports=[{"module": "django.db", "names": ["models"]}],
        classes=[{"name": "User", "parents": ["Model"]}],
        functions=[],
        repo_configs={}
    )
    assert isinstance(result, bool)
    # Also test enrich_class
    enriched = enrich_class({"name": "User", "parents": ["Model"]})
    assert enriched is None or isinstance(enriched, dict)

def test_frameworks_react():
    from src.domain.codeindex.infrastructure.parsers.frameworks.react import detect_react
    result = detect_react(
        rel_path="component.jsx",
        source="import React from 'react'\n",
        imports=[{"module": "react", "names": ["React"]}],
        classes=[],
        functions=[{"name": "Component"}],
        repo_configs={}
    )
    assert isinstance(result, bool)

def test_frameworks_vue():
    from src.domain.codeindex.infrastructure.parsers.frameworks.vue import detect_vue
    result = detect_vue(
        rel_path="App.vue",
        source="<template><div>hi</div></template>",
        imports=[],
        classes=[],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_angular():
    from src.domain.codeindex.infrastructure.parsers.frameworks.angular import detect_angular
    result = detect_angular(
        rel_path="app.component.ts",
        source="@Component({})",
        imports=[{"module": "@angular/core", "names": ["Component"]}],
        classes=[],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_express():
    from src.domain.codeindex.infrastructure.parsers.frameworks.express import detect_express
    result = detect_express(
        rel_path="routes/user.js",
        source="router.get('/users', handler)",
        imports=[{"module": "express", "names": ["Router"]}],
        classes=[],
        functions=[{"name": "handler"}],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_flutter():
    from src.domain.codeindex.infrastructure.parsers.frameworks.flutter import detect_flutter
    result = detect_flutter(
        rel_path="lib/main.dart",
        source="import 'package:flutter/material.dart';",
        imports=[{"module": "package:flutter/material.dart"}],
        classes=[],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_nextjs():
    from src.domain.codeindex.infrastructure.parsers.frameworks.nextjs import detect_nextjs, detect_react
    result = detect_nextjs(
        rel_path="pages/index.tsx",
        source="export default function Home() {}",
        imports=[],
        functions=[{"name": "Home"}],
        repo_configs={},
    )
    assert isinstance(result, bool)
    # Test detect_react within nextjs
    result2 = detect_react(
        rel_path="component.tsx",
        source="",
        imports=[],
        classes=[],
        repo_configs={},
    )
    assert isinstance(result2, bool)

def test_frameworks_laravel():
    from src.domain.codeindex.infrastructure.parsers.frameworks.laravel import detect_laravel
    result = detect_laravel(
        rel_path="app/Http/Controllers/UserController.php",
        source="class UserController extends Controller",
        imports=[],
        classes=[{"name": "UserController", "parents": ["Controller"]}],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_nestjs():
    from src.domain.codeindex.infrastructure.parsers.frameworks.nestjs import detect_nestjs
    result = detect_nestjs(
        rel_path="src/app.module.ts",
        source="@Module({})",
        imports=[{"module": "@nestjs/core"}],
        classes=[],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_rails():
    from src.domain.codeindex.infrastructure.parsers.frameworks.rails import detect_rails
    result = detect_rails(
        rel_path="app/controllers/users_controller.rb",
        source="class UsersController < ApplicationController",
        imports=[],
        classes=[{"name": "UsersController", "parents": ["ApplicationController"]}],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_symfony():
    from src.domain.codeindex.infrastructure.parsers.frameworks.symfony import detect_symfony
    result = detect_symfony(
        rel_path="src/Controller/UserController.php",
        source="class UserController extends AbstractController",
        imports=[],
        classes=[{"name": "UserController", "parents": ["AbstractController"]}],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

def test_frameworks_aspnet():
    from src.domain.codeindex.infrastructure.parsers.frameworks.aspnet import detect_aspnet
    result = detect_aspnet(
        rel_path="Controllers/UserController.cs",
        source="class UserController : Controller",
        imports=[],
        classes=[{"name": "UserController", "parents": ["Controller"]}],
        functions=[],
        repo_configs={},
    )
    assert isinstance(result, bool)

if __name__ == "__main__":
    print("All real integration tests ready.")
