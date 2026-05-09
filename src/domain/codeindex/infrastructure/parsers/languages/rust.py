"""Rust tree-sitter parser — ported from legacy codegraph."""
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

RUST_QUERIES = {
    "functions": """
        (function_item
            name: (identifier) @name
            parameters: (parameters) @params
        ) @function_node
    """,
    "classes": """
        [
            (struct_item name: (type_identifier) @name)
            (enum_item name: (type_identifier) @name)
            (trait_item name: (type_identifier) @name)
        ] @class
    """,
    "imports": """
        (use_declaration) @import
    """,
    "calls": """
        (call_expression
            function: [
                (identifier) @name
                (field_expression field: (field_identifier) @name)
                (scoped_identifier name: (identifier) @name)
            ]
        )
    """,
}


class RustTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = "rust"
        self.language = wrapper.language
        self.parser = wrapper.parser
        self.index_source = False

    def parse(self, path: Path, is_notebook: bool = False, is_dependency: bool = False, index_source: bool = False) -> Dict[str, Any]:
        """Parses a Rust file and returns its structure."""
        self.index_source = index_source
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        functions = self._find_functions(root_node)
        classes = self._find_structs(root_node)
        imports = self._find_imports(root_node)
        function_calls = self._find_calls(root_node)
        traits = self._find_traits(root_node)

        return {
            "path": str(path),
            "functions": functions,
            "classes": classes,
            "traits": traits,
            "variables": [],
            "imports": imports,
            "function_calls": function_calls,
            "is_dependency": is_dependency,
            "lang": self.language_name,
        }

    def _get_node_text(self, node: Any) -> str:
        return node.text.decode("utf-8")

    def _find_functions(self, root_node: Any) -> List[Dict[str, Any]]:
        functions = []
        query_str = "(function_item) @f"

        for func_node, _ in self._execute_query(query_str, root_node):
            name_node = func_node.child_by_field_name("name")
            params_node = func_node.child_by_field_name("parameters")

            if name_node:
                name = self._get_node_text(name_node)
                raw_args = self._parse_function_args(params_node) if params_node else []
                params = []
                for arg in raw_args:
                    arg_str = arg["name"]
                    if arg["type"]:
                        arg_str += f": {arg['type']}"
                    params.append(arg_str)

                func_data = {
                    "name": name,
                    "line_number": name_node.start_point[0] + 1,
                    "end_line": func_node.end_point[0] + 1,
                    "args": params,
                    "lang": self.language_name,
                    "is_dependency": False,
                }

                if self.index_source:
                    func_data["source"] = self._get_node_text(func_node)

                functions.append(func_data)
        return functions

    def _parse_function_args(self, params_node: Any) -> List[Dict[str, Any]]:
        """Helper to parse function arguments from a (parameters) node."""
        args = []
        for param in params_node.named_children:
            arg_info: Dict[str, Any] = {"name": "", "type": None}
            if param.type == "parameter":
                pattern_node = param.child_by_field_name("pattern")
                type_node = param.child_by_field_name("type")
                if pattern_node:
                    arg_info["name"] = self._get_node_text(pattern_node)
                if type_node:
                    arg_info["type"] = self._get_node_text(type_node)
                args.append(arg_info)
            elif param.type == "self_parameter":
                arg_info["name"] = self._get_node_text(param)
                arg_info["type"] = "self"
                args.append(arg_info)
        return args

    def _find_structs(self, root_node: Any) -> List[Dict[str, Any]]:
        structs = []
        query_str = """
        [
            (struct_item) @s
            (enum_item) @e
            (trait_item) @t
        ]
        """
        for item_node, _ in self._execute_query(query_str, root_node):
            name_node = item_node.child_by_field_name("name")
            if not name_node:
                for child in item_node.children:
                    if child.type == "type_identifier":
                        name_node = child
                        break

            if name_node:
                name = self._get_node_text(name_node)
                struct_data = {
                    "name": name,
                    "line_number": name_node.start_point[0] + 1,
                    "end_line": item_node.end_point[0] + 1,
                    "bases": [],
                    "decorators": [],
                    "lang": self.language_name,
                    "is_dependency": False,
                }

                if self.index_source:
                    struct_data["source"] = self._get_node_text(item_node)

                structs.append(struct_data)
        return structs

    def _find_traits(self, root_node: Any) -> List[Dict[str, Any]]:
        traits = []
        query_str = "(trait_item) @trait"
        for trait_node, _ in self._execute_query(query_str, root_node):
            name_node = trait_node.child_by_field_name("name")
            if not name_node:
                for child in trait_node.children:
                    if child.type == "type_identifier":
                        name_node = child
                        break
            if name_node:
                name = self._get_node_text(name_node)
                trait_data = {
                    "name": name,
                    "line_number": name_node.start_point[0] + 1,
                    "end_line": trait_node.end_point[0] + 1,
                }
                if self.index_source:
                    trait_data["source"] = self._get_node_text(trait_node)
                traits.append(trait_data)
        return traits

    def _find_imports(self, root_node: Any) -> List[Dict[str, Any]]:
        imports = []
        query_str = RUST_QUERIES["imports"]
        for node, _ in self._execute_query(query_str, root_node):
            full_import_name = self._get_node_text(node)
            alias = None

            alias_match = re.search(r"as\s+(\w+)\s*;?$", full_import_name)
            if alias_match:
                alias = alias_match.group(1)
                name = alias
            else:
                cleaned_path = re.sub(r";$", "", full_import_name).strip()
                last_part = cleaned_path.split("::")[-1]
                if last_part.strip() == "*":
                    name = "*"
                else:
                    name_match = re.findall(r"(\w+)", last_part)
                    name = name_match[-1] if name_match else last_part

            imports.append(
                {
                    "name": name,
                    "source": full_import_name,
                    "line_number": node.start_point[0] + 1,
                    "alias": alias,
                    "lang": self.language_name
                }
            )
        return imports

    def _find_calls(self, root_node: Any) -> List[Dict[str, Any]]:
        """Finds all function and method calls."""
        calls = []
        query_str = RUST_QUERIES["calls"]
        for node, capture_name in self._execute_query(query_str, root_node):
            if capture_name == "name":
                call_node = node.parent
                while call_node and call_node.type != 'call_expression' and call_node.type != 'source_file':
                    call_node = call_node.parent

                call_name = self._get_node_text(node)

                args = []
                if call_node and call_node.type == 'call_expression':
                    args_node = call_node.child_by_field_name('arguments')
                    if args_node:
                        for child in args_node.children:
                            if child.type not in ('(', ')', ','):
                                args.append(self._get_node_text(child))

                calls.append(
                    {
                        "name": call_name,
                        "full_name": self._get_node_text(call_node) if call_node else call_name,
                        "line_number": node.start_point[0] + 1,
                        "args": args,
                        "inferred_obj_type": None,
                        "context": None,
                        "class_context": None,
                        "lang": self.language_name,
                        "is_dependency": False,
                    }
                )
        return calls

    def _execute_query(self, query_str, root_node):
        """Execute tree-sitter query and yield (node, capture_name) tuples."""
        from src.core.tree_sitter_manager import execute_query
        for node, name in execute_query(self.language, query_str, root_node):
            yield node, name


def pre_scan_rust(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    """Scans Rust files to create a map of function/struct/enum/trait names to their file paths."""
    imports_map = {}
    query_str = """
        (function_item name: (identifier) @name)
        (struct_item name: (type_identifier) @name)
        (enum_item name: (type_identifier) @name)
        (trait_item name: (type_identifier) @name)
    """

    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                tree = parser_wrapper.parser.parse(bytes(f.read(), "utf8"))

            for capture in parser_wrapper.language.query(query_str).captures(tree.root_node):
                name = capture.node.text.decode('utf-8')
                if name not in imports_map:
                    imports_map[name] = []
                imports_map[name].append(str(path.resolve()))
        except Exception:
            pass
    return imports_map
