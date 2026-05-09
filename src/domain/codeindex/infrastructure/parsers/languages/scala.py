"""Scala tree-sitter parser — full implementation with traits, objects, case classes."""
from pathlib import Path
from typing import Any, Dict, List
import re

SCALA_QUERIES = {
    "functions": """
        (function_definition
            name: (identifier) @name
            parameters: (parameters) @params
        ) @function_node
        
        (function_declaration
            name: (identifier) @name
        ) @function_node
    """,
    "classes": """
        [
            (class_definition name: (identifier) @name)
            (trait_definition name: (identifier) @name)
            (object_definition name: (identifier) @name)
            (enum_definition name: (identifier) @name)
            (enum_case_definitions (identifier) @name)
        ] @class
    """,
    "imports": """
        (import_declaration) @import
    """,
    "variables": """
        (val_definition
            name: (identifier) @name
        ) @variable
        
        (var_definition
            name: (identifier) @name
        ) @variable
        
        (pattern
            (identifier) @name
        ) @variable
    """,
    "calls": """
        (call_expression
            function: (identifier) @name
        ) @call_node
        
        (call_expression
            function: (field_expression
                field: (identifier) @name
            )
        ) @call_node
    """,
}


class ScalaTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "scala"
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def parse(self, path: Path, is_dependency: bool = False, is_notebook: bool = False, index_source: bool = False) -> Dict[str, Any]:
        """Parses a Scala file and returns its structure."""
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
        query_str = SCALA_QUERIES['functions']
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
                    parameters = []
                    params_node = node.child_by_field_name("parameters")
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
        query_str = SCALA_QUERIES['classes']
        seen_nodes = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'class':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)

                name_node = node.child_by_field_name('name')
                if not name_node:
                    # Handle enum_case_definitions where name IS the node
                    if node.type == 'identifier':
                        name_node = node

                if name_node:
                    class_name = self._get_node_text(name_node)
                    bases = []

                    # Handle extends/implements in class_definition
                    if node.type == 'class_definition':
                        extends_node = next((c for c in node.children if c.type == 'extends_clause'), None)
                        if extends_node:
                            for child in extends_node.children:
                                if child.type == 'type_identifier':
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
        query_str = SCALA_QUERIES['imports']

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'import':
                import_text = self._get_node_text(node)
                import_match = re.search(r'import\s+(.+)', import_text)
                if import_match:
                    import_path = import_match.group(1).strip()

                    alias = None
                    as_match = re.search(r'\{[^}]*\}\s*$', import_path)
                    if as_match:
                        import_path = import_path[:as_match.start()].strip()

                    imports.append({
                        "name": import_path,
                        "module": import_path,
                        "line_number": node.start_point[0] + 1,
                        "alias": alias,
                    })

        return imports

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = SCALA_QUERIES['variables']
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
        query_str = SCALA_QUERIES['calls']
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
                parts = param.split(":")
                if len(parts) >= 1:
                    param_name = parts[0].strip()
                    params.append(param_name)

        return params

    def _execute_query(self, query_str, root_node):
        """Execute tree-sitter query and yield (node, capture_name) tuples."""
        from src.core.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name


def pre_scan_scala(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    """Scans Scala files to create a map of class/trait/object names to their file paths."""
    name_to_files = {}

    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            class_matches = re.finditer(r'\b(?:abstract\s+)?(?:sealed\s+)?(?:final\s+)?(?:case\s+)?class\s+(\w+)', content)
            for match in class_matches:
                class_name = match.group(1)
                if class_name not in name_to_files:
                    name_to_files[class_name] = []
                name_to_files[class_name].append(str(path))

            trait_matches = re.finditer(r'\b(?:sealed\s+)?trait\s+(\w+)', content)
            for match in trait_matches:
                trait_name = match.group(1)
                if trait_name not in name_to_files:
                    name_to_files[trait_name] = []
                name_to_files[trait_name].append(str(path))

            object_matches = re.finditer(r'\bobject\s+(\w+)', content)
            for match in object_matches:
                object_name = match.group(1)
                if object_name not in name_to_files:
                    name_to_files[object_name] = []
                name_to_files[object_name].append(str(path))

        except Exception:
            pass

    return name_to_files
