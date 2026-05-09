"""
Tests for scope resolution pipeline.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.domain.codeindex.infrastructure.scope_resolution import (
    ScopeTree, ScopeKind, SourceRange, WorkspaceIndex, ScopeExtractor,
    ReferenceResolver, build_workspace_index, resolve_workspace_references,
)


def test_scope_tree_basic():
    tree = ScopeTree("test.py")
    root_id = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1, 0, 50, 0))
    assert tree.root is not None
    assert tree.root.id == root_id
    assert tree.root.kind == ScopeKind.MODULE


def test_scope_tree_add_symbol():
    tree = ScopeTree("test.py")
    root_id = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1, 0, 50, 0))
    sym_id = tree.add_symbol("my_func", "function", root_id, SourceRange(10, 0, 20, 0))
    sym = tree.get_symbol(sym_id)
    assert sym is not None
    assert sym.name == "my_func"
    assert sym.kind == "function"


def test_scope_tree_nested_scopes():
    tree = ScopeTree("test.py")
    mod_id = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1, 0, 50, 0))
    cls_id = tree.add_scope(ScopeKind.CLASS, "MyClass", SourceRange(5, 0, 30, 0), parent_id=mod_id)
    fn_id = tree.add_scope(ScopeKind.FUNCTION, "my_method", SourceRange(10, 0, 20, 0), parent_id=cls_id)
    scope = tree.get_scope(fn_id)
    assert scope is not None
    assert scope.parent_id == cls_id


def test_scope_tree_lookup():
    tree = ScopeTree("test.py")
    mod_id = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1, 0, 50, 0))
    fn_id = tree.add_scope(ScopeKind.FUNCTION, "my_func", SourceRange(10, 0, 20, 0), parent_id=mod_id)
    tree.add_symbol("x", "variable", fn_id, SourceRange(12, 0, 12, 5))
    results = tree.lookup_in_scope("x", fn_id)
    assert len(results) == 1
    results_mod = tree.lookup_in_scope("x", mod_id)
    assert len(results_mod) == 0


def test_scope_tree_lookup_walks_up():
    tree = ScopeTree("test.py")
    mod_id = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1, 0, 50, 0))
    fn_id = tree.add_scope(ScopeKind.FUNCTION, "my_func", SourceRange(10, 0, 20, 0), parent_id=mod_id)
    tree.add_symbol("g", "function", mod_id, SourceRange(5, 0, 8, 0))
    # Should find 'g' defined in parent scope (module) from function scope
    results = tree.lookup_in_scope("g", fn_id)
    assert len(results) == 1


def test_scope_tree_full_name():
    tree = ScopeTree("test.py")
    mod_id = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1, 0, 50, 0))
    cls_id = tree.add_scope(ScopeKind.CLASS, "MyClass", SourceRange(5, 0, 30, 0), parent_id=mod_id)
    sym_id = tree.add_symbol("my_method", "function", cls_id, SourceRange(10, 0, 20, 0))
    sym = tree.get_symbol(sym_id)
    assert sym is not None
    assert "MyClass" in sym.full_name
    assert "my_method" in sym.full_name


def test_workspace_index():
    ws = WorkspaceIndex()
    tree = ScopeTree("main.py")
    mod_id = tree.add_scope(ScopeKind.MODULE, "main", SourceRange(1, 0, 50, 0))
    tree.add_symbol("helper", "function", mod_id, SourceRange(5, 0, 10, 0), is_exported=True)
    ws.add_file(tree)
    assert ws.file_count == 1
    assert ws.total_symbols == 1
    exports = ws.get_exported_symbols("main.py")
    assert len(exports) == 1


def test_scope_extractor():
    extractor = ScopeExtractor()
    parsed = {
        "symbols": [
            {"name": "my_func", "type": "function", "start_line": 5, "end_line": 10, "is_exported": True},
            {"name": "MyClass", "type": "class", "start_line": 15, "end_line": 30, "is_exported": False,
             "children": [
                 {"name": "__init__", "type": "function", "start_line": 16, "end_line": 20},
             ]},
        ]
    }
    tree = extractor.build_scope_tree("test.py", parsed)
    assert tree.symbol_count >= 2
    assert tree.root is not None


def test_reference_resolver():
    ws = WorkspaceIndex()
    
    # File A defines helper
    tree_a = ScopeTree("a.py")
    mod_a = tree_a.add_scope(ScopeKind.MODULE, "a", SourceRange(1, 0, 50, 0))
    tree_a.add_symbol("helper", "function", mod_a, SourceRange(5, 0, 10, 0), is_exported=True)
    ws.add_file(tree_a)
    ws.register_import("b.py", "helper", "a.py")
    
    # File B references helper
    tree_b = ScopeTree("b.py")
    mod_b = tree_b.add_scope(ScopeKind.MODULE, "b", SourceRange(1, 0, 30, 0))
    ref_id = tree_b.add_reference("helper", mod_b, SourceRange(3, 0, 3, 10))
    ws.add_file(tree_b)
    
    resolver = ReferenceResolver(ws)
    stats = resolver.resolve_all()
    assert stats["resolved"] >= 1
    # Check the reference was resolved
    ref = tree_b.get_reference(ref_id)
    assert ref is not None
    assert ref.confidence > 0


def test_build_workspace_index():
    files = [
        {"path": "main.py", "parsed": {"symbols": [{"name": "run", "type": "function", "start_line": 1, "end_line": 5}]}},
    ]
    ws = build_workspace_index(files)
    assert ws.file_count == 1
    assert ws.total_symbols >= 1


def test_resolve_workspace_references():
    ws = WorkspaceIndex()
    tree = ScopeTree("test.py")
    mod_id = tree.add_scope(ScopeKind.MODULE, "test", SourceRange(1, 0, 50, 0))
    tree.add_symbol("helper", "function", mod_id, SourceRange(5, 0, 10, 0))
    tree.add_reference("helper", mod_id, SourceRange(3, 0, 3, 5))
    ws.add_file(tree)
    
    stats = resolve_workspace_references(ws)
    assert stats["total_references"] == 1
    assert stats["resolved"] >= 1


if __name__ == "__main__":
    test_scope_tree_basic()
    test_scope_tree_add_symbol()
    test_scope_tree_nested_scopes()
    test_scope_tree_lookup()
    test_scope_tree_lookup_walks_up()
    test_scope_tree_full_name()
    test_workspace_index()
    test_scope_extractor()
    test_reference_resolver()
    test_build_workspace_index()
    test_resolve_workspace_references()
    print("All scope resolution tests passed!")
