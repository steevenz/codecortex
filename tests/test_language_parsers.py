"""
Tests for COBOL, Vue, and Generic TreeSitter parsers.
REAL tests — no mocks.
"""
import sys, tempfile
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest


# ═══════════════════════════════════════════════════════════════════
# COBOL PARSER
# ═══════════════════════════════════════════════════════════════════

def test_cobol_is_cobol_file():
    from src.domain.codeindex.infrastructure.parsers.languages.cobol import is_cobol_file
    assert is_cobol_file("test.cob") is True
    assert is_cobol_file("test.cbl") is True
    assert is_cobol_file("test.py") is False
    assert is_cobol_file("test.jcl") is True


def test_cobol_parse_program_id():
    from src.domain.codeindex.infrastructure.parsers.languages.cobol import extract_cobol_symbols
    code = "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. HelloWorld.\n       DATA DIVISION.\n       PROCEDURE DIVISION.\n           DISPLAY 'Hello'.\n           STOP RUN.\n"
    result = extract_cobol_symbols("test.cob", code)
    assert result["program_id"] == "HelloWorld"
    symbols = result["symbols"]
    types = {s["type"] for s in symbols}
    assert "program" in types
    assert "division" in types


def test_cobol_parse_data_items():
    from src.domain.codeindex.infrastructure.parsers.languages.cobol import extract_cobol_symbols
    code = "       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n       01 WS-NAME PIC X(30).\n       77 WS-COUNT PIC 9(4) VALUE 0.\n"
    result = extract_cobol_symbols("test.cob", code)
    data_items = [s for s in result["symbols"] if s["type"] == "data_item"]
    assert len(data_items) >= 2
    assert any(s["name"] == "WS-NAME" for s in data_items)


def test_cobol_parse_paragraphs():
    from src.domain.codeindex.infrastructure.parsers.languages.cobol import extract_cobol_symbols
    code = "       PROCEDURE DIVISION.\n       100-MAIN.\n           DISPLAY 'Hello'.\n       200-CLEANUP.\n           STOP RUN.\n"
    result = extract_cobol_symbols("test.cob", code)
    paragraphs = [s for s in result["symbols"] if s["type"] == "paragraph"]
    assert len(paragraphs) >= 2


def test_cobol_parse_via_parser():
    from src.domain.codeindex.infrastructure.parsers.languages.cobol import parse_cobol
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "hello.cob"
        path.write_text("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. Hello.\n       PROCEDURE DIVISION.\n           DISPLAY 'Hello'.\n")
        result = parse_cobol(path)
        assert "error" not in result
        assert result["program_id"] == "Hello"


# ═══════════════════════════════════════════════════════════════════
# VUE PARSER
# ═══════════════════════════════════════════════════════════════════

def test_vue_extract_sections():
    from src.domain.codeindex.infrastructure.parsers.languages.vue import extract_vue_sections
    content = """<template>
  <div>
    <MyComponent />
  </div>
</template>

<script setup>
import { ref } from 'vue'
const count = ref(0)
</script>

<style scoped>
div { color: red }
</style>
"""
    sections = extract_vue_sections(content)
    assert sections["script"] is not None
    assert sections["script_setup"] is True
    assert sections["template"] is not None
    assert "MyComponent" in sections["components"]
    assert len(sections["styles"]) == 1


def test_vue_parse():
    from src.domain.codeindex.infrastructure.parsers.languages.vue import parse_vue
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "App.vue"
        path.write_text("""<template><div><HelloWorld /></div></template>
<script setup>
const msg = 'hello'
</script>""")
        result = parse_vue(path)
        assert "error" not in result
        assert "HelloWorld" in result.get("components", [])


# ═══════════════════════════════════════════════════════════════════
# GENERIC TREESITTER PARSER
# ═══════════════════════════════════════════════════════════════════

def test_generic_parse_julia():
    from src.domain.codeindex.infrastructure.parsers.languages.generic_ts import parse_julia
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.jl"
        path.write_text("function greet(name)\n    println(name)\nend\nstruct Person\n    name::String\nend\n")
        result = parse_julia(path)
        assert isinstance(result, dict)
        assert "language" in result


def test_generic_parse_lua():
    from src.domain.codeindex.infrastructure.parsers.languages.generic_ts import parse_lua
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.lua"
        path.write_text("function greet(name)\n    print(name)\nend\n")
        result = parse_lua(path)
        assert isinstance(result, dict)


def test_generic_parse_zig():
    from src.domain.codeindex.infrastructure.parsers.languages.generic_ts import parse_zig
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.zig"
        path.write_text("fn greet(name: []const u8) void {\n    _ = name;\n}\n")
        result = parse_zig(path)
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════
# LANGUAGE ALIASES
# ═══════════════════════════════════════════════════════════════════

def test_language_aliases():
    from src.core.tree_sitter_manager import get_tree_sitter_manager
    mgr = get_tree_sitter_manager()
    # New aliases should be loadable
    assert mgr._normalize_language_name("vue") == "vue"
    assert mgr._normalize_language_name("cobol") == "cobol"
    assert mgr._normalize_language_name("julia") == "julia"
    assert mgr._normalize_language_name("zig") == "zig"


if __name__ == "__main__":
    print("All language parser tests ready.")
