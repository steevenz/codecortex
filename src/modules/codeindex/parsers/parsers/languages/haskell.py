"""
Haskell tree-sitter parser — full implementation with type classes, data types, modules.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Haskell
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from pathlib import Path
from typing import Any, Dict, List
import re

HASKELL_QUERIES = {
    "functions": """
        (function name: (variable) @name) @function_node
        (signature name: (variable) @name) @function_node
    """,
    "classes": """
        [
            (data_type (type) @name)
            (newtype (type) @name)
            (type_synonym (type) @name)
        ] @class
    """,
    "imports": """
        (import) @import
    """,
    "variables": """
        (pat_left (variable) @name) @variable
        (bind (variable) @name) @variable
    """,
    "calls": """
        (exp_apply (exp_name (variable) @name)) @call_node
        (exp_apply (exp_name (qualified_variable) @name)) @call_node
    """,
}

class HaskellTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "haskell"
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def parse(self, path: Path, is_dependency: bool = False, is_notebook: bool = False, index_source: bool = False) -> Dict[str, Any]:
        self.index_source = index_source
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            if not source_code.strip():
                return {"path": str(path), "functions": [], "classes": [], "variables": [], "imports": [], "function_calls": [], "is_dependency": is_dependency, "lang": self.language_name}
            tree = self.parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node
            functions = self._find_functions(root_node)
            classes = self._find_classes(root_node)
            imports = self._find_imports(root_node)
            variables = self._find_variables(root_node)
            function_calls = self._find_calls(root_node)
            return {"path": str(path), "functions": functions, "classes": classes, "variables": variables, "imports": imports, "function_calls": function_calls, "is_dependency": is_dependency, "lang": self.language_name}
        except Exception:
            return {"path": str(path), "functions": [], "classes": [], "variables": [], "imports": [], "function_calls": [], "is_dependency": is_dependency, "lang": self.language_name}

    def _get_node_text(self, node: Any) -> str:
        if not node:
            return ""
        return node.text.decode("utf-8")

    def _find_functions(self, root_node) -> List[Dict[str, Any]]:
        functions = []
        query_str = HASKELL_QUERIES['functions']
        seen_nodes = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'function_node':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                name_node = node.child_by_field_name("name")
                if name_node:
                    func_name = self._get_node_text(name_node)
                    args = []
                    # Haskell params are variable nodes after the name before the body
                    is_name = True
                    for child in node.named_children:
                        if child == name_node:
                            is_name = False
                            continue
                        if is_name:
                            continue
                        if child.type == "variable":
                            args.append(self._get_node_text(child))
                    func_data = {
                        "name": func_name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "args": args,
                        "cyclomatic_complexity": 1,
                        "context": None,
                        "context_type": None,
                        "class_context": None,
                        "decorators": [],
                        "function_calls": [],
                        "lang": self.language_name,
                        "is_dependency": False,
                    }
                    if self.index_source:
                        func_data["source"] = self._get_node_text(node)
                    functions.append(func_data)
        return functions

    def _find_classes(self, root_node) -> List[Dict[str, Any]]:
        classes = []
        query_str = HASKELL_QUERIES['classes']
        seen_nodes = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'class':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                name = self._get_node_text(node)
                first_word = name.strip().split()[0] if name.strip() else "unknown"
                class_data = {
                    "name": first_word,
                    "line_number": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "bases": [],
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                if self.index_source:
                    class_data["source"] = self._get_node_text(node)
                classes.append(class_data)
        return classes

    def _find_imports(self, root_node) -> List[Dict[str, Any]]:
        imports = []
        query_str = HASKELL_QUERIES['imports']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'import':
                import_text = self._get_node_text(node)
                line_number = node.start_point[0] + 1
                import_match = re.search(r'import\s+(?:qualified\s+)?(\S+)', import_text)
                if import_match:
                    import_path = import_match.group(1).strip()
                    alias = None
                    as_match = re.search(r'\bas\s+(\w+)', import_text)
                    if as_match:
                        alias = as_match.group(1)
                    imports.append({"name": import_path, "module": import_path, "line_number": line_number, "alias": alias})
        return imports

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = HASKELL_QUERIES['variables']
        seen_vars = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                var_name = self._get_node_text(node)
                start_line = node.start_point[0] + 1
                start_byte = node.start_byte
                if start_byte in seen_vars:
                    continue
                seen_vars.add(start_byte)
                variables.append({"name": var_name, "type": None, "line_number": start_line})
        return variables

    def _find_calls(self, root_node) -> List[Dict[str, Any]]:
        calls = []
        query_str = HASKELL_QUERIES['calls']
        seen_calls = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                call_name = self._get_node_text(node)
                line_number = node.start_point[0] + 1
                call_key = f"{call_name}_{line_number}"
                if call_key in seen_calls:
                    continue
                seen_calls.add(call_key)
                calls.append({"name": call_name, "line_number": line_number})
        return calls

    def _execute_query(self, query_str, root_node):
        from src.core.parser.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name

def pre_scan_haskell(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    name_to_files = {}
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for pattern, decl_type in [(r'^(?:data|newtype|type)\s+(\w+)', 'type'), (r'^class\s+[^=]*=>\s*(\w+)|^class\s+(\w+)', 'class')]:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    name = match.group(1) or match.group(2)
                    if name:
                        if name not in name_to_files:
                            name_to_files[name] = []
                        name_to_files[name].append(str(path))
        except Exception:
            pass
    return name_to_files
