import os
from pathlib import Path


def test_graph_manager_defaults_to_none_backend() -> None:
    os.environ.pop("CODECORTEX_GRAPH_BACKEND", None)
    os.environ.pop("CODECORTEX_GRAPH_BACKEND_REQUIRED", None)

    from src.core.graph_manager import GraphManager, NoOpBackend

    gm = GraphManager()
    assert gm.get_backend_type() in {"none", "noop"}
    backend = gm.get_backend()
    assert isinstance(backend, NoOpBackend)
    assert backend.is_connected() is True
    with backend.get_session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS cnt")
        assert result.single() is None


def test_tree_sitter_manager_loads_python_and_tsx_languages() -> None:
    from src.core.tree_sitter_manager import get_tree_sitter_manager

    mgr = get_tree_sitter_manager()

    lang_py = mgr.get_language_safe("python")
    assert lang_py is not None
    parser_py = mgr.create_parser("python")
    tree = parser_py.parse(b"def a():\n  return 1\n")
    assert tree is not None

    lang_tsx = mgr.get_language_safe("tsx")
    assert lang_tsx is not None
    parser_tsx = mgr.create_parser("tsx")
    tree2 = parser_tsx.parse(b"export const A = () => (<div/>);\n")
    assert tree2 is not None

