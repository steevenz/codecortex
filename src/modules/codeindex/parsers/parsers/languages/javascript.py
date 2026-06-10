"""
JavaScript tree-sitter parser — ported from legacy codegraph.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Javascript
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

JS_QUERIES = {
    "functions": """
        (function_declaration 
            name: (identifier) @name
            parameters: (formal_parameters) @params
        ) @function_node
        
        (variable_declarator 
            name: (identifier) @name 
            value: (function_expression 
                parameters: (formal_parameters) @params
            ) @function_node
        )
        
        (variable_declarator 
            name: (identifier) @name 
            value: (arrow_function 
                parameters: (formal_parameters) @params
            ) @function_node
        )
        
        (variable_declarator 
            name: (identifier) @name 
            value: (arrow_function 
                parameter: (identifier) @single_param
            ) @function_node
        )
        
        (method_definition 
            name: (property_identifier) @name
            parameters: (formal_parameters) @params
        ) @function_node
        
        (assignment_expression
            left: (member_expression 
                property: (property_identifier) @name
            )
            right: (function_expression
                parameters: (formal_parameters) @params
            ) @function_node
        )
        
        (assignment_expression
            left: (member_expression 
                property: (property_identifier) @name
            )
            right: (arrow_function
                parameters: (formal_parameters) @params
            ) @function_node
        )
    """,
    "classes": """
        (class_declaration) @class
        (class) @class
    """,
    "imports": """
        (import_statement) @import
        (call_expression
            function: (identifier) @require_call (#eq? @require_call "require")
        ) @import
    """,
    "calls": """
        (call_expression function: (identifier) @name)
        (call_expression function: (member_expression property: (property_identifier) @name))
        (new_expression constructor: (identifier) @name)
        (new_expression constructor: (member_expression property: (property_identifier) @name))
    """,
    "variables": """
        (variable_declarator name: (identifier) @name)
    """,
}

_GETTER_RE = re.compile(r"^\s*(?:static\s+)?get\b")
_SETTER_RE = re.compile(r"^\s*(?:static\s+)?set\b")
_STATIC_RE = re.compile(r"^\s*static\b")

def _first_line_before_body(text: str) -> str:
    """Best-effort header extraction: take text before the first '{'."""
    head = text.split("{", 1)[0]
    if not head.strip():
        return text.splitlines()[0] if text.splitlines() else text
    return head

def _classify_method_kind(header: str) -> Optional[str]:
    """Return 'getter' | 'setter' | 'static' | None."""
    if _GETTER_RE.search(header):
        return "getter"
    if _SETTER_RE.search(header):
        return "setter"
    if _STATIC_RE.search(header):
        return "static"
    return None

class JavascriptTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = wrapper.language_name
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def parse(self, path: Path, is_notebook: bool = False, is_dependency: bool = False, index_source: bool = False) -> Dict[str, Any]:
        """Parses a JavaScript file and returns its structure."""
        self.index_source = index_source
        with open(path, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        functions = self._find_functions(root_node)
        classes = self._find_classes(root_node)
        imports = self._find_imports(root_node)
        function_calls = self._find_calls(root_node)
        variables = self._find_variables(root_node)

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

    def _get_node_text(self, node) -> str:
        return node.text.decode('utf-8')

    def _find_functions(self, root_node) -> List[Dict[str, Any]]:
        functions = []
        query_str = JS_QUERIES['functions']

        def _fn_for_name(name_node):
            current = name_node.parent
            while current:
                if current.type in ('function_declaration', 'function', 'arrow_function', 'method_definition', 'function_expression'):
                    return current
                elif current.type in ('variable_declarator', 'assignment_expression'):
                    for child in current.children:
                        if child.type in ('function', 'arrow_function', 'function_expression'):
                            return child
                current = current.parent
            return None

        def _fn_for_params(params_node):
            current = params_node.parent
            while current:
                if current.type in ('function_declaration', 'function', 'arrow_function', 'method_definition', 'function_expression'):
                    return current
                current = current.parent
            return None

        def _key(n):
            return (n.start_byte, n.end_byte, n.type)

        captures_by_function = {}

        def _bucket_for(node):
            fid = _key(node)
            return captures_by_function.setdefault(fid, {
                'node': node, 'name': None, 'params': None, 'single_param': None
            })

        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'function_node':
                _bucket_for(node)
            elif capture_name == 'name':
                fn = _fn_for_name(node)
                if fn:
                    b = _bucket_for(fn)
                    b['name'] = self._get_node_text(node)
            elif capture_name == 'params':
                fn = _fn_for_params(node)
                if fn:
                    b = _bucket_for(fn)
                    b['params'] = node
            elif capture_name == 'single_param':
                fn = _fn_for_params(node)
                if fn:
                    b = _bucket_for(fn)
                    b['single_param'] = node

        for _, data in captures_by_function.items():
            func_node = data['node']
            name = data.get('name')
            if not name and func_node.type == 'method_definition':
                nm = func_node.child_by_field_name('name')
                if nm:
                    name = self._get_node_text(nm)
            if not name:
                continue

            args = []
            if data.get('params'):
                args = self._extract_parameters(data['params'])
            elif data.get('single_param'):
                args = [self._get_node_text(data['single_param'])]

            docstring = self._get_jsdoc_comment(func_node)

            js_kind = None
            if func_node.type == 'method_definition':
                header = _first_line_before_body(self._get_node_text(func_node))
                js_kind = _classify_method_kind(header)

            func_data = {
                "name": name,
                "line_number": func_node.start_point[0] + 1,
                "end_line": func_node.end_point[0] + 1,
                "args": args,
                "lang": self.language_name,
                "is_dependency": False,
            }

            if self.index_source:
                func_data["source"] = self._get_node_text(func_node)
                func_data["docstring"] = docstring
            if js_kind is not None:
                func_data["type"] = js_kind

            functions.append(func_data)

        return functions

    def _extract_parameters(self, params_node) -> List[str]:
        params = []
        if params_node.type == 'formal_parameters':
            for child in params_node.children:
                if child.type == 'identifier':
                    params.append(self._get_node_text(child))
                elif child.type == 'assignment_pattern':
                    left_child = child.child_by_field_name('left')
                    if left_child and left_child.type == 'identifier':
                        params.append(self._get_node_text(left_child))
                elif child.type == 'rest_pattern':
                    argument = child.child_by_field_name('argument')
                    if argument and argument.type == 'identifier':
                        params.append(f"...{self._get_node_text(argument)}")
        return params

    def _get_jsdoc_comment(self, func_node) -> Optional[str]:
        prev_sibling = func_node.prev_sibling
        while prev_sibling and prev_sibling.type in ('comment', '\n', ' '):
            if prev_sibling.type == 'comment':
                comment_text = self._get_node_text(prev_sibling)
                if comment_text.startswith('/**') and comment_text.endswith('*/'):
                    return comment_text.strip()
            prev_sibling = prev_sibling.prev_sibling
        return None

    def _find_classes(self, root_node) -> List[Dict[str, Any]]:
        classes = []
        query_str = JS_QUERIES['classes']
        for class_node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'class':
                name_node = class_node.child_by_field_name('name')
                if not name_node:
                    continue
                name = self._get_node_text(name_node)

                bases = []
                heritage_node = next((child for child in class_node.children if child.type == 'class_heritage'), None)
                if heritage_node:
                    if heritage_node.named_child_count > 0:
                        base_expr_node = heritage_node.named_child(0)
                        bases.append(self._get_node_text(base_expr_node))
                    elif heritage_node.child_count > 0:
                        base_expr_node = heritage_node.child(heritage_node.child_count - 1)
                        bases.append(self._get_node_text(base_expr_node))

                class_data = {
                    "name": name,
                    "line_number": class_node.start_point[0] + 1,
                    "end_line": class_node.end_point[0] + 1,
                    "bases": bases,
                    "context": None,
                    "decorators": [],
                    "lang": self.language_name,
                    "is_dependency": False,
                }

                if self.index_source:
                    class_data["source"] = self._get_node_text(class_node)
                    class_data["docstring"] = self._get_jsdoc_comment(class_node)

                classes.append(class_data)
        return classes

    def _find_imports(self, root_node) -> List[Dict[str, Any]]:
        imports = []
        query_str = JS_QUERIES['imports']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name != 'import':
                continue

            line_number = node.start_point[0] + 1

            if node.type == 'import_statement':
                source = self._get_node_text(node.child_by_field_name('source')).strip('\'"')

                import_clause = node.child_by_field_name('import')
                if not import_clause:
                    imports.append({'name': source, 'source': source, 'alias': None, 'line_number': line_number,
                                    'lang': self.language_name})
                    continue

                if import_clause.type == 'identifier':
                    alias = self._get_node_text(import_clause)
                    imports.append({'name': 'default', 'source': source, 'alias': alias, 'line_number': line_number,
                                    'lang': self.language_name})
                elif import_clause.type == 'namespace_import':
                    alias_node = import_clause.child_by_field_name('alias')
                    if alias_node:
                        alias = self._get_node_text(alias_node)
                        imports.append({'name': '*', 'source': source, 'alias': alias, 'line_number': line_number,
                                        'lang': self.language_name})
                elif import_clause.type == 'named_imports':
                    for specifier in import_clause.children:
                        if specifier.type == 'import_specifier':
                            name_node = specifier.child_by_field_name('name')
                            alias_node = specifier.child_by_field_name('alias')
                            original_name = self._get_node_text(name_node)
                            alias = self._get_node_text(alias_node) if alias_node else None
                            imports.append(
                                {'name': original_name, 'source': source, 'alias': alias, 'line_number': line_number,
                                 'lang': self.language_name})

            elif node.type == 'call_expression':
                args = node.child_by_field_name('arguments')
                if not args or args.named_child_count == 0:
                    continue
                source_node = args.named_child(0)
                if not source_node or source_node.type != 'string':
                    continue
                source = self._get_node_text(source_node).strip('\'"')

                alias = None
                if node.parent.type == 'variable_declarator':
                    alias_node = node.parent.child_by_field_name('name')
                    if alias_node:
                        alias = self._get_node_text(alias_node)
                imports.append({'name': source, 'source': source, 'alias': alias, 'line_number': line_number,
                                'lang': self.language_name})

        return imports

    def _find_calls(self, root_node) -> List[Dict[str, Any]]:
        calls = []
        query_str = JS_QUERIES['calls']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                call_node = node.parent
                while call_node and call_node.type != 'call_expression' and call_node.type != 'program':
                    call_node = call_node.parent

                name = self._get_node_text(node)
                args = []
                arguments_node = None
                if call_node and call_node.type in ('call_expression', 'new_expression'):
                    arguments_node = call_node.child_by_field_name('arguments')

                if arguments_node:
                    for arg in arguments_node.children:
                        if arg.type not in ('(', ')', ','):
                            args.append(self._get_node_text(arg))

                call_data = {
                    "name": name,
                    "full_name": self._get_node_text(call_node),
                    "line_number": node.start_point[0] + 1,
                    "args": args,
                    "inferred_obj_type": None,
                    "context": None,
                    "class_context": None,
                    "lang": self.language_name,
                    "is_dependency": False,
                }
                calls.append(call_data)
        return calls

    def _find_variables(self, root_node) -> List[Dict[str, Any]]:
        variables = []
        query_str = JS_QUERIES['variables']
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == 'name':
                var_node = node.parent
                name = self._get_node_text(node)
                value = None
                type_text = None

                value_node = var_node.child_by_field_name("value") if var_node else None

                if value_node:
                    value_type = value_node.type
                    if value_type in ("function_expression", "arrow_function"):
                        continue
                    if "function" in value_type or "arrow" in value_type:
                        continue

                    if value_type == "call_expression":
                        func_node = value_node.child_by_field_name("function")
                        value = self._get_node_text(func_node) if func_node else name
                    else:
                        value = self._get_node_text(value_node)

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

    def _execute_query(self, query_str, root_node):
        """Execute tree-sitter query and yield (node, capture_name) tuples."""
        from src.core.parser.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name

def pre_scan_javascript(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    """Scans JavaScript files to create a map of class/function names to their file paths."""
    imports_map = {}
    query_str = """
        (class_declaration name: (identifier) @name)
        (function_declaration name: (identifier) @name)
        (variable_declarator name: (identifier) @name value: (function_expression))
        (variable_declarator name: (identifier) @name value: (arrow_function))
        (method_definition name: (property_identifier) @name)
        (assignment_expression
            left: (member_expression 
                property: (property_identifier) @name
            )
            right: (function_expression)
        )
        (assignment_expression
            left: (member_expression 
                property: (property_identifier) @name
            )
            right: (arrow_function)
        )
    """

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = parser_wrapper.parser.parse(bytes(f.read(), "utf8"))

            for capture in parser_wrapper.language.query(query_str).captures(tree.root_node):
                name = capture.node.text.decode('utf-8')
                if name not in imports_map:
                    imports_map[name] = []
                imports_map[name].append(str(path.resolve()))
        except Exception:
            pass
    return imports_map
