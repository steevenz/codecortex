"""
Perl tree-sitter parser — full implementation with packages, subroutines, modules.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Perl
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

PERL_QUERIES = {
    "functions": """
        (function_definition name: (function_name) @name) @function_node
    """,
    "classes": """
        (package name: (bareword) @name) @class
    """,
    "imports": """
        (use_statement module: (_) @module) @import
        (require_expression (bareword) @module) @import
        (do_expression (string_literal) @module) @import
    """,
    "variables": """
        (variable_declaration variable: (_) @name) @variable
        (array_variable) @variable
        (hash_variable) @variable
        (scalar_variable) @variable
    """,
    "calls": """
        (function_call function: (function_name) @name) @call_node
        (method_call function: (function_name) @name) @call_node
    """,
}

class PerlTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "perl"
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

    def _get_class_context(self, fn_node) -> Optional[str]:
        current = fn_node.parent
        while current:
            if current.type == "package":
                name_node = current.child_by_field_name("name")
                if name_node:
                    return self._get_node_text(name_node)
            current = current.parent
        return None

    def _find_functions(self, root_node) -> List[Dict[str, Any]]:
        functions = []
        query_str = PERL_QUERIES['functions']
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
                    # Extract parameters from variable children after name
                    for child in node.named_children:
                        if child.start_byte > name_node.end_byte and child.type == "variable":
                            args.append(self._get_node_text(child))
                    class_ctx = self._get_class_context(node)
                    func_data = {
                        "name": func_name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "args": args,
                        "cyclomatic_complexity": 1,
                        "context": None,
                        "context_type": None,
                        "class_context": class_ctx,
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
        query_str = PERL_QUERIES['classes']
        seen_nodes = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'class':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_name = self._get_node_text(name_node)
                    class_data = {
                        "name": class_name,
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
        query_str = PERL_QUERIES['imports']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'import':
                import_text = self._get_node_text(node)
                line_number = node.start_point[0] + 1
                # Parse use/require/do
                module_match = re.search(r'(?:use|require|do)\s+([\w:]+)', import_text)
                if module_match:
                    module_name = module_match.group(1)
                    imports.append({"name": module_name, "module": module_name, "line_number": line_number, "alias": None})
        return imports

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = PERL_QUERIES['variables']
        seen_vars = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'variable':
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
        query_str = PERL_QUERIES['calls']
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

def pre_scan_perl(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    name_to_files = {}
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            package_matches = re.finditer(r'\bpackage\s+([\w:]+)', content)
            for match in package_matches:
                package_name = match.group(1)
                if package_name not in name_to_files:
                    name_to_files[package_name] = []
                name_to_files[package_name].append(str(path))
            sub_matches = re.finditer(r'\bsub\s+(\w+)', content)
            for match in sub_matches:
                sub_name = match.group(1)
                if sub_name not in name_to_files:
                    name_to_files[sub_name] = []
                name_to_files[sub_name].append(str(path))
        except Exception:
            pass
    return name_to_files
