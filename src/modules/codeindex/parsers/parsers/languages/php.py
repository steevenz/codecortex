"""
PHP tree-sitter parser — full implementation with traits, namespaces, closures.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Php
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

PHP_QUERIES = {
    "functions": """
        (function_definition
            name: (name) @name
            parameters: (formal_parameters) @params
        ) @function_node

        (method_declaration
            name: (name) @name
            parameters: (formal_parameters) @params
        ) @function_node

        (arrow_function
            name: (name) @name
            parameters: (formal_parameters) @params
        ) @function_node

        (anonymous_function_creation_expression
            parameters: (formal_parameters) @params
        ) @function_node
    """,
    "classes": """
        [
            (class_declaration name: (name) @name)
            (interface_declaration name: (name) @name)
            (trait_declaration name: (name) @name)
            (enum_declaration name: (name) @name)
        ] @class
    """,
    "imports": """
        (use_declaration) @import

        (namespace_name) @namespace
    """,
    "variables": """
        (expression_statement
            (assignment_expression
                left: (variable_name) @name
            )
        ) @variable

        (property_declaration
            (property_element
                name: (variable_name) @name
            )
        ) @variable
    """,
    "calls": """
        (function_call_expression
            function: (name) @name
        ) @call_node

        (function_call_expression
            function: (qualified_name) @name
        ) @call_node

        (member_call_expression
            name: (name) @name
        ) @call_node
    """,
}

class PhpTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "php"
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def parse(self, path: Path, is_dependency: bool = False, is_notebook: bool = False, index_source: bool = False) -> Dict[str, Any]:
        """Parses a PHP file and returns its structure."""
        self.index_source = index_source
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()

            if not source_code.strip():
                return {
                    "path": str(path),
                    "functions": [],
                    "classes": [],
                    "variables": [],
                    "imports": [],
                    "function_calls": [],
                    "is_dependency": is_dependency,
                    "lang": self.language_name,
                }

            tree = self.parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node

            functions = self._find_functions(root_node)
            classes = self._find_classes(root_node)
            imports = self._find_imports(root_node)
            variables = self._find_variables(root_node)
            function_calls = self._find_calls(root_node)

            return {
                "path": str(path),
                "functions": functions,
                "classes": classes,
                "variables": variables,
                "imports": imports,
                "function_calls": function_calls,
                "is_dependency": is_dependency,
                "lang": self.language_name,
            }

        except Exception:
            return {
                "path": str(path),
                "functions": [],
                "classes": [],
                "variables": [],
                "imports": [],
                "function_calls": [],
                "is_dependency": is_dependency,
                "lang": self.language_name,
            }

    def _get_node_text(self, node: Any) -> str:
        if not node:
            return ""
        return node.text.decode("utf-8")

    def _get_class_context(self, fn_node) -> Optional[str]:
        current = fn_node.parent
        while current:
            if current.type in ("class_declaration", "trait_declaration"):
                name_node = current.child_by_field_name("name")
                if name_node:
                    return self._get_node_text(name_node)
            current = current.parent
        return None

    def _find_functions(self, root_node) -> List[Dict[str, Any]]:
        functions = []
        query_str = PHP_QUERIES['functions']
        seen_nodes = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'function_node':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)

                name_node = node.child_by_field_name("name")
                params_node = node.child_by_field_name("parameters")

                func_name = "anonymous"
                if name_node:
                    func_name = self._get_node_text(name_node)
                elif node.type == "anonymous_function_creation_expression":
                    func_name = "anonymous"

                parameters = []
                if params_node:
                    params_text = self._get_node_text(params_node)
                    parameters = self._extract_parameter_names(params_text)

                class_ctx = self._get_class_context(node)
                func_data = {
                    "name": func_name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "args": parameters,
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
        query_str = PHP_QUERIES['classes']
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
                    bases = []

                    # Handle extends and implements
                    extends_node = node.child_by_field_name('extends')
                    if extends_node:
                        for child in extends_node.children:
                            if child.type == 'name':
                                bases.append(self._get_node_text(child))

                    implements_node = node.child_by_field_name('implements')
                    if implements_node:
                        for child in implements_node.children:
                            if child.type == 'name':
                                bases.append(self._get_node_text(child))

                    class_data = {
                        "name": class_name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "bases": bases,
                        "lang": self.language_name,
                        "is_dependency": False,
                    }

                    if self.index_source:
                        class_data["source"] = self._get_node_text(node)

                    classes.append(class_data)

        return classes

    def _find_imports(self, root_node) -> List[Dict[str, Any]]:
        imports = []
        query_str = PHP_QUERIES['imports']

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'import':
                import_text = self._get_node_text(node)
                # Handle use statements
                use_match = re.search(r'use\s+([^;]+)', import_text)
                if use_match:
                    import_path = use_match.group(1).strip()

                    # Extract alias if present
                    alias = None
                    as_match = re.search(r'\bas\s+(\w+)', import_path)
                    if as_match:
                        alias = as_match.group(1)
                        import_path = import_path.split(' as ')[0].strip()

                    imports.append({
                        "name": import_path,
                        "module": import_path,
                        "line_number": node.start_point[0] + 1,
                        "alias": alias,
                    })
            elif capture_name == 'namespace':
                namespace_text = self._get_node_text(node)
                imports.append({
                    "name": namespace_text,
                    "module": namespace_text,
                    "line_number": node.start_point[0] + 1,
                    "alias": None,
                })

        return imports

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = PHP_QUERIES['variables']
        seen_vars = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                var_name = self._get_node_text(node)
                # Remove $ prefix if present
                var_name = var_name.lstrip('$')
                start_line = node.start_point[0] + 1

                start_byte = node.start_byte
                if start_byte in seen_vars:
                    continue
                seen_vars.add(start_byte)

                variables.append({
                    "name": var_name,
                    "type": None,
                    "line_number": start_line,
                })

        return variables

    def _find_calls(self, root_node) -> List[Dict[str, Any]]:
        calls = []
        query_str = PHP_QUERIES['calls']
        seen_calls = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                call_name = self._get_node_text(node)
                line_number = node.start_point[0] + 1

                call_node = node.parent
                while call_node and call_node.type not in ("function_call_expression", "member_call_expression"):
                    call_node = call_node.parent

                if not call_node:
                    call_node = node

                call_key = f"{call_name}_{line_number}"
                if call_key in seen_calls:
                    continue
                seen_calls.add(call_key)

                calls.append({
                    "name": call_name,
                    "line_number": line_number,
                })

        return calls

    def _extract_parameter_names(self, params_text: str) -> List[str]:
        params = []
        if not params_text or params_text.strip() == "()":
            return params

        params_content = params_text.strip("()")
        if not params_content:
            return params

        for param in params_content.split(","):
            param = param.strip()
            if param:
                # PHP parameters: $name, Type $name, $name = default
                parts = param.split()
                for part in parts:
                    if part.startswith('$'):
                        param_name = part.lstrip('$')
                        params.append(param_name)
                        break

        return params

    def _execute_query(self, query_str, root_node):
        """Execute tree-sitter query and yield (node, capture_name) tuples."""
        from src.core.parser.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name

def pre_scan_php(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    """Scans PHP files to create a map of class/interface/trait names to their file paths."""
    name_to_files = {}

    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            class_matches = re.finditer(r'\b(?:final\s+)?(?:abstract\s+)?class\s+(\w+)', content)
            for match in class_matches:
                class_name = match.group(1)
                if class_name not in name_to_files:
                    name_to_files[class_name] = []
                name_to_files[class_name].append(str(path))

            interface_matches = re.finditer(r'\binterface\s+(\w+)', content)
            for match in interface_matches:
                interface_name = match.group(1)
                if interface_name not in name_to_files:
                    name_to_files[interface_name] = []
                name_to_files[interface_name].append(str(path))

            trait_matches = re.finditer(r'\btrait\s+(\w+)', content)
            for match in trait_matches:
                trait_name = match.group(1)
                if trait_name not in name_to_files:
                    name_to_files[trait_name] = []
                name_to_files[trait_name].append(str(path))

        except Exception:
            pass

    return name_to_files
