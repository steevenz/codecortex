"""Dart tree-sitter parser — full implementation with mixins, extensions, generics."""
from pathlib import Path
from typing import Any, Dict, List
import re

DART_QUERIES = {
    "functions": """
        (function_signature
            name: (identifier) @name
            formal_parameters: (formal_parameter_list) @params
        ) @function_node
        
        (method_signature
            name: (identifier) @name
            formal_parameters: (formal_parameter_list) @params
        ) @function_node
        
        (constructor_signature
            name: (identifier) @name
            formal_parameters: (formal_parameter_list) @params
        ) @function_node
    """,
    "classes": """
        [
            (class_definition name: (identifier) @name)
            (mixin_declaration name: (identifier) @name)
            (extension_declaration name: (identifier) @name)
            (enum_declaration name: (identifier) @name)
        ] @class
    """,
    "imports": """
        (import_or_export) @import
    """,
    "variables": """
        (final_or_const_variable_declaration
            (initialized_variable_definition
                name: (identifier) @name
            )
        ) @variable
        
        (variable_declaration
            (initialized_variable_definition
                name: (identifier) @name
            )
        ) @variable
        
        (initialized_identifier
            name: (identifier) @name
        ) @variable
    """,
    "calls": """
        (function_expression_invocation
            function: (identifier) @name
        ) @call_node
        
        (method_invocation
            function: (identifier) @name
        ) @call_node
        
        (constructor_invocation
            type: (_) @name
        ) @call_node
    """,
}


class DartTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "dart"
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def parse(self, path: Path, is_dependency: bool = False, is_notebook: bool = False, index_source: bool = False) -> Dict[str, Any]:
        """Parses a Dart file and returns its structure."""
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

    def _find_functions(self, root_node) -> List[Dict[str, Any]]:
        functions = []
        query_str = DART_QUERIES['functions']
        seen_nodes = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'function_node':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)

                name_node = node.child_by_field_name("name")
                params_node = node.child_by_field_name("formal_parameters")

                if name_node:
                    func_name = self._get_node_text(name_node)
                    parameters = []
                    if params_node:
                        params_text = self._get_node_text(params_node)
                        parameters = self._extract_parameter_names(params_text)

                    func_data = {
                        "name": func_name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "args": parameters,
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
        query_str = DART_QUERIES['classes']
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

                    superclass_node = node.child_by_field_name('superclass')
                    if superclass_node:
                        bases.append(self._get_node_text(superclass_node))

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
        query_str = DART_QUERIES['imports']

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'import':
                import_text = self._get_node_text(node)
                import_match = re.search(r"import\s+['\"]([^'\"]+)['\"]", import_text)
                if not import_match:
                    import_match = re.search(r"import\s+(.+)", import_text)
                if import_match:
                    import_path = import_match.group(1).strip()
                    alias = None
                    as_match = re.search(r'\bas\s+(\w+)', import_text)
                    if as_match:
                        alias = as_match.group(1)

                    imports.append({
                        "name": import_path,
                        "module": import_path,
                        "line_number": node.start_point[0] + 1,
                        "alias": alias,
                    })

        return imports

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = DART_QUERIES['variables']
        seen_vars = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                var_name = self._get_node_text(node)
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
        query_str = DART_QUERIES['calls']
        seen_calls = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                call_name = self._get_node_text(node)
                line_number = node.start_point[0] + 1

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
                parts = param.split()
                for part in parts:
                    if not part.startswith("<") and not part.endswith(">"):
                        params.append(part.rstrip("?"))
                        break

        return params

    def _execute_query(self, query_str, root_node):
        """Execute tree-sitter query and yield (node, capture_name) tuples."""
        from src.core.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name


def pre_scan_dart(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    """Scans Dart files to create a map of class/mixin/enum names to their file paths."""
    name_to_files = {}

    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            class_matches = re.finditer(r'\b(?:abstract\s+)?class\s+(\w+)', content)
            for match in class_matches:
                class_name = match.group(1)
                if class_name not in name_to_files:
                    name_to_files[class_name] = []
                name_to_files[class_name].append(str(path))

            mixin_matches = re.finditer(r'\bmixin\s+(\w+)', content)
            for match in mixin_matches:
                mixin_name = match.group(1)
                if mixin_name not in name_to_files:
                    name_to_files[mixin_name] = []
                name_to_files[mixin_name].append(str(path))

            enum_matches = re.finditer(r'\benum\s+(\w+)', content)
            for match in enum_matches:
                enum_name = match.group(1)
                if enum_name not in name_to_files:
                    name_to_files[enum_name] = []
                name_to_files[enum_name].append(str(path))

        except Exception:
            pass

    return name_to_files
