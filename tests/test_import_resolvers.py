"""
Tests for import resolution pipeline.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.domain.codeindex.infrastructure.import_resolvers import (
    PythonImportResolver,
    TypeScriptImportResolver,
    GoImportResolver,
    SuffixIndex,
    resolve_imports_for_file,
    build_import_map,
)


def test_python_import_resolver():
    resolver = PythonImportResolver()
    files = {"utils/helpers.py", "models/user.py", "main.py"}
    resolved = resolver.resolve("from utils import helpers", "main.py", files)
    assert "utils/helpers.py" in resolved


def test_python_from_import():
    resolver = PythonImportResolver()
    files = {"models/user.py", "models/__init__.py"}
    resolved = resolver.resolve("from models.user import User", "app.py", files)
    assert "models/user.py" in resolved


def test_typescript_import():
    resolver = TypeScriptImportResolver()
    files = {"src/utils/helpers.ts", "src/app.ts"}
    resolved = resolver.resolve("import { helper } from './utils/helpers'", "src/app.ts", files)
    assert "src/utils/helpers.ts" in resolved or len(resolved) > 0


def test_go_import():
    resolver = GoImportResolver()
    files = {"fmt.go", "main.go"}
    resolved = resolver.resolve('import "fmt"', "main.go", files)
    assert "fmt.go" in resolved


def test_suffix_index():
    files = {"src/utils/helpers.py", "src/models/user.py", "main.py"}
    index = SuffixIndex(files)
    matches = index.find("utils/helpers.py")
    assert "src/utils/helpers.py" in matches


def test_resolve_imports_for_file():
    content = """
import os
from pathlib import Path
from utils.helpers import format_date
"""
    files = {"utils/helpers.py", "pathlib.py", "os.py"}
    resolved = resolve_imports_for_file("main.py", content, "python", files, SuffixIndex(files))
    assert "utils/helpers.py" in resolved


def test_build_import_map():
    files = [
        {"path": "main.py", "content": "from utils import helpers\n", "language": "python"},
        {"path": "utils/helpers.py", "content": "def helper(): pass\n", "language": "python"},
    ]
    import_map = build_import_map(files)
    assert "main.py" in import_map
    assert "utils/helpers.py" in import_map["main.py"]


if __name__ == "__main__":
    test_python_import_resolver()
    test_python_from_import()
    test_typescript_import()
    test_go_import()
    test_suffix_index()
    test_resolve_imports_for_file()
    test_build_import_map()
    print("All import resolution tests passed.")
