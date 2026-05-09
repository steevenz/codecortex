"""Java tree-sitter parser — ported from legacy codegraph."""
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

JAVA_QUERIES = {
    "functions": """
        (method_declaration
            name: (identifier) @name
            parameters: (formal_parameters) @params
        ) @function_node
        
        (constructor_declaration
            name: (identifier) @name
            parameters: (formal_parameters) @params
        ) @function_node
    """,
    "classes": """
        [
            (class_declaration name: (identifier) @name)
            (interface_declaration name: (identifier) @name)
            (enum_declaration name: (identifier) @name)
            (annotation_type_declaration name: (identifier) @name)
        ] @class
    """,
    "imports": """
        (import_declaration) @import
    """,
    "variables": """
        (local_variable_declaration
            type: (_) @type
            declarator: (variable_declarator
                name: (identifier) @name
            )
        ) @variable
        
        (field_declaration
            type: (_) @type
            declarator: (variable_declarator
                name: (identifier) @name
            )
        ) @variable
    """,
    "calls": """
        (method_invocation
            name: (identifier) @name
        ) @call_node
        
        (object_creation_expression
            type: [
                (type_identifier)
                (scoped_type_identifier)
                (generic_type)
            ] @name
        ) @call_node
    """,
}


class JavaTreeSitterParser:
    @staticmethod
    def _strip_generic(type_str: str) -> str:
        """Return the raw type name without generic parameters, e.g. 'List<String>' -> 'List'."""
        bracket = type_str.find('<')
        return type_str[:bracket].strip() if bracket != -1 else type_str.strip()

    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "java"
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def parse(self, path: Path, is_notebook: bool = False, is_dependency: bool = False, index_source: bool = False) -> Dict[str, Any]:
        """Parses a Java file and returns its structure."""
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
        query_str = JAVA_QUERIES['functions']
        seen_nodes = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'function_node':
                node_id = (node.start_byte, node.end_byte, node.type)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)

                name_node = node.child_by_field_name("name")
                params_node = node.child_by_field_name("parameters")

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
                        "lang": self.language_name,
                        "is_dependency": False,
                    }

                    if self.index_source:
                        func_data["source"] = self._get_node_text(node)

                    functions.append(func_data)

        return functions

    def _find_classes(self, root_node) -> List[Dict[str, Any]]:
        classes = []
        query_str = JAVA_QUERIES['classes']
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

                    interfaces_node = node.child_by_field_name('interfaces')
                    if not interfaces_node:
                        interfaces_node = next((c for c in node.children if c.type == 'super_interfaces'), None)

                    if interfaces_node:
                        type_list = interfaces_node.child_by_field_name('list')
                        if not type_list:
                            type_list = next((c for c in interfaces_node.children if c.type == 'type_list'), None)

                        if type_list:
                            for child in type_list.children:
                                if child.type in ('type_identifier', 'generic_type', 'scoped_type_identifier'):
                                    bases.append(self._get_node_text(child))
                        else:
                            for child in interfaces_node.children:
                                if child.type in ('type_identifier', 'generic_type', 'scoped_type_identifier'):
                                    bases.append(self._get_node_text(child))

                    class_data = {
                        "name": class_name,
                        "line_number": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "bases": bases,
                        "decorators": [],
                        "lang": self.language_name,
                        "is_dependency": False,
                    }

                    if self.index_source:
                        class_data["source"] = self._get_node_text(node)

                    classes.append(class_data)

        return classes

    def _find_imports(self, root_node) -> List[Dict[str, Any]]:
        imports = []
        query_str = JAVA_QUERIES['imports']

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'import':
                import_text = self._get_node_text(node)
                import_match = re.search(r'import\s+(?:static\s+)?([^;]+)', import_text)
                if import_match:
                    import_path = import_match.group(1).strip()

                    imports.append({
                        "name": import_path,
                        "source": import_path,
                        "line_number": node.start_point[0] + 1,
                        "alias": None,
                        "lang": self.language_name
                    })

        return imports

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = JAVA_QUERIES['variables']
        seen_vars = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                if node.parent.type == "variable_declarator":
                    var_name = self._get_node_text(node)
                    start_line = node.start_point[0] + 1

                    declaration = node.parent.parent
                    type_node = declaration.child_by_field_name("type")
                    var_type = self._get_node_text(type_node) if type_node else "Unknown"

                    start_byte = node.start_byte
                    if start_byte in seen_vars:
                        continue
                    seen_vars.add(start_byte)

                    variables.append({
                        "name": var_name,
                        "type": var_type,
                        "line_number": start_line,
                        "value": None,
                        "context": None,
                        "class_context": None,
                        "lang": self.language_name,
                        "is_dependency": False,
                    })

        return variables

    def _find_calls(self, root_node) -> List[Dict[str, Any]]:
        calls = []
        query_str = JAVA_QUERIES['calls']
        seen_calls = set()

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                call_name = self._get_node_text(node)
                line_number = node.start_point[0] + 1

                call_node = node.parent
                while call_node and call_node.type not in ("method_invocation", "object_creation_expression"):
                    call_node = call_node.parent

                if not call_node:
                    call_node = node

                call_key = f"{call_name}_{line_number}"
                if call_key in seen_calls:
                    continue
                seen_calls.add(call_key)

                args = []
                if call_node:
                    args_node = next((c for c in call_node.children if c.type == 'argument_list'), None)
                    if args_node:
                        for arg in args_node.children:
                            if arg.type not in ('(', ')', ','):
                                args.append(self._get_node_text(arg))

                full_name = call_name
                if call_node.type == 'method_invocation':
                    obj_node = call_node.child_by_field_name('object')
                    if obj_node:
                        obj_text = self._get_node_text(obj_node)
                        full_name = f"{obj_text}.{call_name}"
                elif call_node.type == 'object_creation_expression':
                    type_node = call_node.child_by_field_name('type')
                    if type_node:
                        full_name = self._get_node_text(type_node)

                calls.append({
                    "name": call_name,
                    "full_name": full_name,
                    "line_number": line_number,
                    "args": args,
                    "inferred_obj_type": None,
                    "context": None,
                    "class_context": None,
                    "lang": self.language_name,
                    "is_dependency": False,
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
                if len(parts) >= 2:
                    param_name = parts[-1]
                    params.append(param_name)

        return params

    def _execute_query(self, query_str, root_node):
        """Execute tree-sitter query and yield (node, capture_name) tuples."""
        from src.core.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name


def pre_scan_java(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    """Scans Java files to create a map of class/interface names to their file paths."""
    name_to_files = {}

    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            class_matches = re.finditer(r'\b(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)', content)
            for match in class_matches:
                class_name = match.group(1)
                if class_name not in name_to_files:
                    name_to_files[class_name] = []
                name_to_files[class_name].append(str(path))

            interface_matches = re.finditer(r'\b(?:public\s+|private\s+|protected\s+)?interface\s+(\w+)', content)
            for match in interface_matches:
                interface_name = match.group(1)
                if interface_name not in name_to_files:
                    name_to_files[interface_name] = []
                name_to_files[interface_name].append(str(path))

        except Exception:
            pass

    return name_to_files
