"""
Tests for Service Boundary Detection, MRO, and Wildcard Imports.
ALL real code, no mocks.
"""
import sys, tempfile
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest


# ═══════════════════════════════════════════════════════════════════
# SERVICE BOUNDARY DETECTION
# ═══════════════════════════════════════════════════════════════════

def test_sbd_by_markers():
    from src.domain.codegraph.application.service_boundary import detect_service_boundaries
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        svc_dir = root / "users-service"
        svc_dir.mkdir()
        (svc_dir / "package.json").write_text('{"name": "users-service"}')
        (svc_dir / "Dockerfile").write_text("FROM python:3.14")
        services = detect_service_boundaries(root)
        assert len(services) >= 1
        assert any(s["name"] == "users-service" for s in services)


def test_sbd_by_http_routes():
    from src.domain.codegraph.application.service_boundary import detect_service_boundaries
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        api = root / "api"
        api.mkdir()
        (api / "main.py").write_text("@app.get('/users')\ndef list_users(): pass\n@app.post('/users')\ndef create(): pass\n")
        services = detect_service_boundaries(root)
        assert len(services) >= 1


def test_sbd_service_boundary_class():
    from src.domain.codegraph.application.service_boundary import ServiceBoundary
    svc = ServiceBoundary(service_path="./api", service_name="api", markers=["package.json"], routes=["/users"])
    assert svc.service_name == "api"
    assert len(svc.markers) == 1


# ═══════════════════════════════════════════════════════════════════
# MRO - METHOD RESOLUTION ORDER
# ═══════════════════════════════════════════════════════════════════

def test_mro_simple():
    from src.domain.codegraph.application.mro import c3_linearize
    heritage = {"D": ["B", "C"], "B": ["A"], "C": ["A"], "A": []}
    mro = c3_linearize("D", heritage)
    assert mro == ["D", "B", "C", "A"]


def test_mro_diamond():
    from src.domain.codegraph.application.mro import c3_linearize
    # Diamond inheritance: D(B, C), B(A), C(A)
    heritage = {"D": ["B", "C"], "B": ["A"], "C": ["A"], "A": []}
    mro = c3_linearize("D", heritage)
    assert mro.index("B") < mro.index("C")  # B before C
    assert mro.index("C") < mro.index("A")  # C before A


def test_mro_single():
    from src.domain.codegraph.application.mro import c3_linearize
    heritage = {"B": ["A"], "A": []}
    mro = c3_linearize("B", heritage)
    assert mro == ["B", "A"]


def test_mro_no_parents():
    from src.domain.codegraph.application.mro import c3_linearize
    mro = c3_linearize("A", {"A": []})
    assert mro == ["A"]


def test_mro_compute():
    from src.domain.codegraph.application.mro import compute_mro
    heritage = {"D": ["B", "C"], "B": ["A"], "C": ["A"], "A": []}
    mro_map = compute_mro(heritage)
    assert "D" in mro_map
    assert len(mro_map["D"]) == 4


def test_mro_detect_overrides():
    from src.domain.codegraph.application.mro import detect_method_overrides, compute_mro
    from src.domain.codegraph.application.mro import ClassInfo
    classes = {
        "A": ClassInfo(name="A", bases=[], methods=["speak"], file_path="a.py"),
        "B": ClassInfo(name="B", bases=["A"], methods=["speak", "run"], file_path="b.py"),
        "C": ClassInfo(name="C", bases=["A"], methods=["speak"], file_path="c.py"),
    }
    mro_map = compute_mro({"A": [], "B": ["A"], "C": ["A"]})
    overrides = detect_method_overrides(classes, mro_map)
    assert len(overrides) >= 1


def test_mro_build_heritage():
    from src.domain.codegraph.application.mro import build_heritage_map_from_symbols
    symbols = [
        {"name": "D", "type": "class", "parents": ["B", "C"]},
        {"name": "B", "type": "class", "parents": ["A"]},
        {"name": "C", "type": "class", "parents": ["A"]},
    ]
    heritage = build_heritage_map_from_symbols(symbols)
    assert heritage["D"] == ["B", "C"]


# ═══════════════════════════════════════════════════════════════════
# WILDCARD IMPORTS
# ═══════════════════════════════════════════════════════════════════

def test_wi_is_wildcard():
    from src.domain.codeindex.infrastructure.wildcard_imports import is_wildcard_import
    assert is_wildcard_import("from utils import *") is True
    assert is_wildcard_import("import os") is False
    assert is_wildcard_import("from utils import helper") is False


def test_wi_get_exported_python():
    from src.domain.codeindex.infrastructure.wildcard_imports import get_exported_symbols
    content = """
def public_func():
    pass

class MyClass:
    pass

def _private():
    pass

CONSTANT = 42
"""
    exported = get_exported_symbols(content, "python")
    assert "public_func" in exported
    assert "MyClass" in exported
    assert "CONSTANT" in exported
    assert "_private" not in exported


def test_wi_get_exported_python_all():
    from src.domain.codeindex.infrastructure.wildcard_imports import get_exported_symbols
    content = '__all__ = ["explicit_only", "another_one"]\ndef hidden(): pass\n'
    exported = get_exported_symbols(content, "python")
    assert exported == ["explicit_only", "another_one"]


def test_wi_get_exported_ts():
    from src.domain.codeindex.infrastructure.wildcard_imports import get_exported_symbols
    content = """
export function hello() {}
export class User {}
const internal = 42;
export const API_URL = "/api";
"""
    exported = get_exported_symbols(content, "typescript")
    assert "hello" in exported
    assert "User" in exported
    assert "API_URL" in exported
    assert "internal" not in exported


def test_wi_get_exported_go():
    from src.domain.codeindex.infrastructure.wildcard_imports import get_exported_symbols
    content = "func PublicFunc() {}\nfunc privateFunc() {}\ntype User struct {}\ntype config struct {}\n"
    exported = get_exported_symbols(content, "go")
    assert "PublicFunc" in exported
    assert "User" in exported
    assert "privateFunc" not in exported
    assert "config" not in exported


def test_wi_synthesize():
    from src.domain.codeindex.infrastructure.wildcard_imports import synthesize_wildcard_imports
    files = {
        "utils/helpers.py": "def format_date(): pass\ndef parse_csv(): pass\n",
        "main.py": "from utils.helpers import *\n",
    }
    lang_map = {"utils/helpers.py": "python", "main.py": "python"}
    result = synthesize_wildcard_imports(files, lang_map)
    assert "main.py" in result
    assert "format_date" in result["main.py"]
    assert "parse_csv" in result["main.py"]


def test_wi_quick_resolve():
    from src.domain.codeindex.infrastructure.wildcard_imports import quick_wildcard_resolve
    files = {"utils/tools.py": "def hammer(): pass\ndef saw(): pass\n"}
    lang_map = {"utils/tools.py": "python"}
    result = quick_wildcard_resolve("main.py", "from utils.tools import *", files, lang_map)
    assert "hammer" in result
    assert "saw" in result


if __name__ == "__main__":
    print("All 16 new tests ready for pytest.")
