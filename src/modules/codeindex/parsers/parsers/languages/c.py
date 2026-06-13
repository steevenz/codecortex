"""
C parser — tree-sitter based symbol extraction.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.C
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from pathlib import Path
from typing import Any, Dict, List
from src.core.parser.tree_sitter_manager import execute_query

C_QUERIES = {
    "functions": "(function_definition declarator: (function_declarator declarator: (identifier) @name)) @function_node",
    "structs": "(struct_specifier name: (type_identifier) @name) @struct",
    "enums": "(enum_specifier name: (type_identifier) @name) @enum",
    "imports": "(preproc_include path: [(string_literal) @path (system_lib_string) @path]) @import",
    "calls": "(call_expression function: [(identifier) @name (field_expression field: (field_identifier) @method_name)])",
    "variables": "(declaration declarator: (init_declarator declarator: (identifier) @name))",
}

class CTreeSitterParser:
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.language_name = wrapper.language_name
        self.language = wrapper.language
        self.parser = wrapper.parser

    def _text(self, node) -> str:
        return node.text.decode("utf-8")

    def parse(self, path: Path, is_dependency: bool = False, **kwargs) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()
            tree = self.parser.parse(bytes(src, "utf8"))
            root = tree.root_node
            return {
                "path": str(path),
                "functions": self._find_functions(root),
                "classes": self._find_structs(root) + self._find_enums(root),
                "variables": self._find_variables(root),
                "imports": self._find_imports(root),
                "function_calls": self._find_calls(root),
                "is_dependency": is_dependency,
                "lang": self.language_name,
            }
        except Exception as e:
            return {"path": str(path), "error": str(e), "lang": self.language_name}

    def _find_functions(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, C_QUERIES["functions"], root):
            if tag == "name":
                fn = n.parent
                while fn and fn.type != "function_definition":
                    fn = fn.parent
                if not fn:
                    continue
                params = fn.child_by_field_name("declarator")
                if params:
                    params = params.child_by_field_name("parameters")
                args = []
                if params:
                    for p in params.children:
                        t = self._text(p) if p.type == "identifier" else None
                        if t:
                            args.append(t)
                out.append({
                    "name": self._text(n),
                    "line_number": n.start_point[0] + 1,
                    "end_line": fn.end_point[0] + 1,
                    "args": args,
                    "lang": self.language_name,
                    "is_dependency": False,
                })
        return out

    def _find_structs(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, C_QUERIES["structs"], root):
            if tag == "name":
                struct_node = n.parent
                while struct_node and struct_node.type != "struct_specifier":
                    struct_node = struct_node.parent
                out.append({
                    "name": self._text(n),
                    "line_number": n.start_point[0] + 1,
                    "end_line": struct_node.end_point[0] + 1 if struct_node else n.end_point[0] + 1,
                    "bases": [],
                    "lang": self.language_name,
                    "is_dependency": False,
                })
        return out

    def _find_enums(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, C_QUERIES["enums"], root):
            if tag == "name":
                out.append({
                    "name": self._text(n),
                    "line_number": n.start_point[0] + 1,
                    "end_line": n.end_point[0] + 1,
                    "bases": [],
                    "lang": self.language_name,
                    "is_dependency": False,
                })
        return out

    def _find_imports(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, C_QUERIES["imports"], root):
            if tag == "path":
                out.append({
                    "name": self._text(n).strip('"<>'),
                    "source": self._text(n),
                    "line_number": n.start_point[0] + 1,
                    "lang": self.language_name,
                })
        return out

    def _find_calls(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, C_QUERIES["calls"], root):
            name = self._text(n)
            out.append({
                "name": name,
                "line_number": n.start_point[0] + 1,
                "lang": self.language_name,
            })
        return out

    def _find_variables(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, C_QUERIES["variables"], root):
            if tag == "name":
                out.append({
                    "name": self._text(n),
                    "line_number": n.start_point[0] + 1,
                    "lang": self.language_name,
                })
        return out
