"""C++ tree-sitter parser — ported from legacy codegraph."""
from pathlib import Path
from typing import Any, Dict, List, Optional

CPP_QUERIES = {
    "functions": """
        (function_definition
            declarator: (function_declarator
                declarator: [
                    (identifier) @name
                    (field_identifier) @name
                    (qualified_identifier) @qualified_name
                ]
            )
        ) @function_node
    """,
    "classes": """
        (class_specifier
            name: (type_identifier) @name
        ) @class
    """,
    "imports": """
        (preproc_include
            path: [
                (string_literal) @path
                (system_lib_string) @path
            ]
        ) @import
    """,
    "calls": """
        (call_expression
            function: [
                (identifier) @function_name
                (field_expression
                    field: (field_identifier) @method_name
                )
                (qualified_identifier) @scoped_name
            ]
        arguments: (argument_list) @args
    )
    """,
    "enums": """
        (enum_specifier
            name: (type_identifier) @name
            body: (enumerator_list
                (enumerator
                    name: (identifier) @value
                    )*
                )? @body
        ) @enum
    """,
    "structs": """
        (struct_specifier
            name: (type_identifier) @name
            body: (field_declaration_list)? @body
        ) @struct
    """,
    "unions": """
        (union_specifier
            name: (type_identifier)? @name
            body: (field_declaration_list
                (field_declaration
                    declarator: [
                        (field_identifier) @value
                        (pointer_declarator (field_identifier) @value)
                        (array_declarator (field_identifier) @value)
                        ]
                    )*
                )? @body
        ) @union
    """,
    "macros": """
        (preproc_def
            name: (identifier) @name
        ) @macro
    """,
    "variables": """
        (declaration
            declarator: (init_declarator
                            declarator: (identifier) @name))
        (declaration
            declarator: (init_declarator
                            declarator: (pointer_declarator
                                declarator: (identifier) @name)))
        (field_declaration
            declarator: [
                 (field_identifier) @name
                 (pointer_declarator declarator: (field_identifier) @name)
                 (array_declarator declarator: (field_identifier) @name)
                 (reference_declarator (field_identifier) @name)
            ]
        )
    """,
    "lambda_assignments": """
        (declaration
            declarator: (init_declarator
                declarator: (identifier) @name
                value: (lambda_expression) @lambda_node))
    """,
}


class CppTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "cpp"
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def _get_node_text(self, node) -> str:
        return node.text.decode('utf-8')

    def parse(self, path: Path, is_notebook: bool = False, is_dependency: bool = False, index_source: bool = False) -> Dict[str, Any]:
        """Parses a C++ file and returns its structure."""
        self.index_source = index_source
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        functions = self._find_functions(root_node)
        functions.extend(self._find_lambda_assignments(root_node))
        function_calls = self._find_calls(root_node)
        classes = self._find_classes(root_node)
        imports = self._find_imports(root_node)
        structs = self._find_structs(root_node)
        enums = self._find_enums(root_node)
        unions = self._find_unions(root_node)
        macros = self._find_macros(root_node)
        variables = self._find_variables(root_node)

        return {
            "path": str(path),
            "functions": functions,
            "classes": classes,
            "structs": structs,
            "enums": enums,
            "unions": unions,
            "macros": macros,
            "variables": variables,
            "declarations": [],
            "imports": imports,
            "function_calls": function_calls,
            "is_dependency": is_dependency,
            "lang": self.language_name,
        }

    def _find_functions(self, root_node):
        functions = []
        query_str = CPP_QUERIES['functions']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name in ('name', 'qualified_name'):
                func_node = node.parent
                while func_node and func_node.type != 'function_definition':
                    func_node = func_node.parent

                if not func_node:
                    continue

                raw_text = self._get_node_text(node)
                class_context = None
                if capture_name == 'qualified_name' and '::' in raw_text:
                    parts = raw_text.rsplit('::', 1)
                    class_context = parts[0]
                    name = parts[1]
                else:
                    name = raw_text

                params = self._extract_function_params(func_node)

                func_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": func_node.end_point[0] + 1,
                    "args": params,
                    "lang": self.language_name,
                    "is_dependency": False,
                }

                if class_context:
                    func_data["class_context"] = class_context

                if self.index_source:
                    func_data["source"] = self._get_node_text(func_node)

                functions.append(func_data)
        return functions

    def _extract_function_params(self, func_node) -> List[str]:
        params = []
        declarator_node = func_node.child_by_field_name('declarator')
        if not declarator_node:
            return params

        parameters_node = declarator_node.child_by_field_name('parameters')
        if not parameters_node or parameters_node.type != 'parameter_list':
            return params

        for param in parameters_node.children:
            if param.type == 'parameter_declaration':
                param_decl = param.child_by_field_name('declarator')
                while param_decl and param_decl.type not in ('identifier', 'field_identifier', 'type_identifier'):
                    child = param_decl.child_by_field_name('declarator')
                    if child:
                        param_decl = child
                    else:
                        break

                name = self._get_node_text(param_decl) if param_decl else ""
                param_type_node = param.child_by_field_name('type')
                type_str = self._get_node_text(param_type_node) if param_type_node else ""

                if name:
                    if type_str:
                        params.append(f"{type_str} {name}")
                    else:
                        params.append(name)
        return params

    def _find_classes(self, root_node):
        classes = []
        query_str = CPP_QUERIES['classes']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                class_node = node.parent
                name = self._get_node_text(node)
                bases = self._extract_base_classes(class_node)
                class_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": class_node.end_point[0] + 1,
                    "bases": bases,
                    "decorators": [],
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                if self.index_source:
                    class_data["source"] = self._get_node_text(class_node)
                classes.append(class_data)
        return classes

    def _extract_base_classes(self, class_node) -> List[str]:
        bases = []
        for child in class_node.children:
            if child.type == 'base_class_clause':
                for base_spec in child.children:
                    if base_spec.type in ('base_class_specifier', 'type_identifier', 'qualified_identifier', 'template_type'):
                        if base_spec.type == 'base_class_specifier':
                            for sub in base_spec.children:
                                if sub.type in ('type_identifier', 'qualified_identifier', 'template_type'):
                                    base_name = self._get_node_text(sub)
                                    if '<' in base_name:
                                        base_name = base_name[:base_name.index('<')].strip()
                                    bases.append(base_name)
                                    break
                        else:
                            base_name = self._get_node_text(base_spec)
                            if '<' in base_name:
                                base_name = base_name[:base_name.index('<')].strip()
                            bases.append(base_name)
                break
        return bases

    def _find_imports(self, root_node):
        imports = []
        query_str = CPP_QUERIES['imports']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'path':
                path_text = self._get_node_text(node).strip('<>')
                imports.append({
                    "name": path_text,
                    "source": path_text,
                    "line_number": node.start_point[0] + 1,
                    "alias": None,
                    "lang": self.language_name
                })
        return imports

    def _find_enums(self, root_node):
        enums = []
        query_str = CPP_QUERIES['enums']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                name = self._get_node_text(node)
                enum_node = node.parent
                enum_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": enum_node.end_point[0] + 1,
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                if self.index_source:
                    enum_data["source"] = self._get_node_text(enum_node)
                enums.append(enum_data)
        return enums

    def _find_structs(self, root_node):
        structs = []
        query_str = CPP_QUERIES['structs']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                name = self._get_node_text(node)
                struct_node = node.parent
                struct_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": struct_node.end_point[0] + 1,
                    "bases": [],
                    "decorators": [],
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                if self.index_source:
                    struct_data["source"] = self._get_node_text(struct_node)
                structs.append(struct_data)
        return structs

    def _find_unions(self, root_node):
        unions = []
        query_str = CPP_QUERIES['unions']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                name = self._get_node_text(node)
                union_node = node.parent
                union_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": union_node.end_point[0] + 1,
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                if self.index_source:
                    union_data["source"] = self._get_node_text(union_node)
                unions.append(union_data)
        return unions

    def _find_macros(self, root_node):
        macros = []
        query_str = CPP_QUERIES['macros']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                macro_node = node.parent
                name = self._get_node_text(node)
                macro_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": macro_node.end_point[0] + 1,
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                if self.index_source:
                    macro_data["source"] = self._get_node_text(macro_node)
                macros.append(macro_data)
        return macros

    def _find_lambda_assignments(self, root_node):
        functions = []
        query_str = CPP_QUERIES.get('lambda_assignments')
        if not query_str:
            return functions

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                assignment_node = node.parent
                lambda_node = assignment_node.child_by_field_name('value')
                if lambda_node is None or lambda_node.type != 'lambda_expression':
                    continue

                name = self._get_node_text(node)
                params_node = lambda_node.child_by_field_name('parameters')

                func_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "end_line": assignment_node.end_point[0] + 1,
                    "args": [self._get_node_text(p) for p in params_node.children if p.type == 'identifier'] if params_node else [],
                    "lang": self.language_name,
                    "is_dependency": False,
                }

                if self.index_source:
                    func_data["source"] = self._get_node_text(assignment_node)

                functions.append(func_data)
        return functions

    def _find_variables(self, root_node):
        variables = []
        query_str = CPP_QUERIES['variables']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                assignment_node = node.parent

                right_node = assignment_node.child_by_field_name('value')
                if right_node and right_node.type == 'lambda_expression':
                    continue

                name = self._get_node_text(node)
                value = self._get_node_text(right_node) if right_node else None

                type_node = assignment_node.child_by_field_name('type')
                type_text = self._get_node_text(type_node) if type_node else None

                variable_data = {
                    "name": name,
                    "line_number": node.start_point[0] + 1,
                    "value": value,
                    "type": type_text,
                    "context": None,
                    "class_context": None,
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                variables.append(variable_data)
        return variables

    def _find_calls(self, root_node):
        calls = []
        query_str = CPP_QUERIES['calls']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name in ("function_name", "method_name", "scoped_name"):
                raw_text = self._get_node_text(node)

                inferred_obj_type = None
                if capture_name == "scoped_name" and '::' in raw_text:
                    parts = raw_text.rsplit('::', 1)
                    func_name = parts[1]
                    inferred_obj_type = parts[0]
                elif capture_name == "method_name":
                    func_name = raw_text
                    field_expr = node.parent
                    if field_expr and field_expr.type == 'field_expression':
                        obj_node = field_expr.child_by_field_name('argument')
                        if obj_node:
                            obj_text = self._get_node_text(obj_node)
                            if obj_text == 'this':
                                inferred_obj_type = 'this'
                            else:
                                inferred_obj_type = obj_text
                else:
                    func_name = raw_text

                call_data = {
                    "name": func_name,
                    "full_name": raw_text,
                    "line_number": node.start_point[0] + 1,
                    "args": [],
                    "inferred_obj_type": inferred_obj_type,
                    "context": None,
                    "class_context": None,
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                calls.append(call_data)
        return calls

    def _execute_query(self, query_str, root_node):
        """Execute tree-sitter query and yield (node, capture_name) tuples."""
        from src.core.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name


def pre_scan_cpp(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    """Scans C++ files to create a map of top-level class, struct, and function names to their file paths."""
    imports_map = {}
    query_str = """
        (class_specifier name: (type_identifier) @name)
        (struct_specifier name: (type_identifier) @name)
        (function_definition declarator: (function_declarator declarator: (identifier) @name))
        (function_definition declarator: (function_declarator declarator: (qualified_identifier) @qualified_name))
    """

    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                source_bytes = f.read().encode("utf-8")
                tree = parser_wrapper.parser.parse(source_bytes)

            for node, capture_name in parser_wrapper.language.query(query_str).captures(tree.root_node):
                resolved_path = str(path.resolve())
                if capture_name == "name":
                    name = node.text.decode("utf-8")
                    paths = imports_map.setdefault(name, [])
                    if resolved_path not in paths:
                        paths.append(resolved_path)
                elif capture_name == "qualified_name":
                    full_name = node.text.decode("utf-8")
                    paths = imports_map.setdefault(full_name, [])
                    if resolved_path not in paths:
                        paths.append(resolved_path)
                    if '::' in full_name:
                        method_name = full_name.rsplit('::', 1)[1]
                        paths = imports_map.setdefault(method_name, [])
                        if resolved_path not in paths:
                            paths.append(resolved_path)
        except Exception:
            pass

    return imports_map
