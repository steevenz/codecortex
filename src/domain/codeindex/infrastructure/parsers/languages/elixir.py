"""Elixir tree-sitter parser — full implementation with modules, macros, structs, pipelines."""
from pathlib import Path
from typing import Any, Dict, List
import re

ELIXIR_QUERIES = {
    "functions": """
        (call
            target: (identifier) @name
            (arguments)
        ) @function_node
        
        (call
            target: (dot
                right: (identifier) @name
            )
            (arguments)
        ) @function_node
        
        (function_clause
            name: (identifier) @name
        ) @function_node
        
        (macro_clause
            name: (identifier) @name
        ) @function_node
    """,
    "classes": """
        [
            (call
                target: (identifier) @name (#match? @name "defmodule|defprotocol|defimpl|defstruct")
                (arguments (alias) @class_name)
            ) @class
            (alias) @class
        ] @class
    """,
    "imports": """
        (call
            target: (identifier) @method (#match? @method "alias|import|require|use")
        ) @import
    """,
    "variables": """
        (identifier) @variable
        
        (module_attribute) @variable
    """,
    "calls": """
        (call
            target: (identifier) @name
            (arguments)
        ) @call_node
        
        (call
            target: (dot
                right: (identifier) @name
            )
        ) @call_node
    """,
}


class ElixirTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "elixir"
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
        query_str = ELIXIR_QUERIES['functions']
        seen_nodes = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'function_node':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                name_node = None
                # Try to find name in child nodes
                for child in node.children:
                    if child.type in ('identifier', 'property_identifier') and child.start_byte >= node.start_byte and child.end_byte <= node.end_byte:
                        name_node = child
                        break
                    elif child.type == 'dot':
                        for sub in child.children:
                            if sub.type in ('identifier', 'property_identifier'):
                                name_node = sub
                                break
                if not name_node:
                    continue
                func_name = self._get_node_text(name_node)
                # Skip if this is a module/import call, not a function definition
                if func_name in ('def', 'defp', 'defmacro', 'defmacrop'):
                    # For def/defp, the function name is in the arguments
                    args_node = node.child_by_field_name("arguments")
                    if args_node and len(args_node.children) > 0:
                        first_arg = args_node.children[0]
                        if first_arg.type == 'identifier':
                            func_name = self._get_node_text(first_arg)
                        elif first_arg.type == 'call':
                            func_name = self._get_node_text(first_arg.child_by_field_name("function"))
                        else:
                            continue
                    else:
                        continue
                func_data = {
                    "name": func_name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "args": [],
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
        query_str = ELIXIR_QUERIES['classes']
        seen_nodes = set()
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'class':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                if node.type == 'alias':
                    class_name = self._get_node_text(node)
                else:
                    # For call nodes, extract from alias in arguments
                    class_name = self._get_node_text(node)
                    alias_match = re.search(r'alias\s+(\w+)', class_name)
                    if alias_match:
                        class_name = alias_match.group(1)
                    else:
                        # Try to find alias child
                        alias_child = next((c for c in node.children if c.type == 'alias'), None)
                        if alias_child:
                            class_name = self._get_node_text(alias_child)
                        else:
                            continue
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
        query_str = ELIXIR_QUERIES['imports']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'import':
                import_text = self._get_node_text(node)
                line_number = node.start_point[0] + 1
                # Match alias, import, require, use with module name
                for pattern in [r'\b(alias|import|require|use)\s+(\S+)']:
                    match = re.search(pattern, import_text)
                    if match:
                        module_name = match.group(2).strip()
                        imports.append({"name": module_name, "module": module_name, "line_number": line_number, "alias": None})
                        break
        return imports

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = ELIXIR_QUERIES['variables']
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
        query_str = ELIXIR_QUERIES['calls']
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
        query = self.language.query(query_str)
        for capture in query.captures(root_node):
            yield capture.node, capture.name


def pre_scan_elixir(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    name_to_files = {}
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            module_matches = re.finditer(r'\bdefmodule\s+(\S+)\s+do', content)
            for match in module_matches:
                module_name = match.group(1).strip()
                if module_name not in name_to_files:
                    name_to_files[module_name] = []
                name_to_files[module_name].append(str(path))
            alias_matches = re.finditer(r'\balias\s+(\S+)', content)
            for match in alias_matches:
                alias_name = match.group(1).strip()
                if alias_name not in name_to_files:
                    name_to_files[alias_name] = []
                name_to_files[alias_name].append(str(path))
        except Exception:
            pass
    return name_to_files
