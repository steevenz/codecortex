"""
CSS/SCSS parser — regex-based with tree-sitter fallback.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Languages.Css
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

class CSSTreeSitterParser:
    """Parse CSS and SCSS files for symbol extraction."""

    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = wrapper.language_name
        self.language = wrapper.language
        self.parser = wrapper.parser

    def _text(self, node) -> str:
        return node.text.decode("utf-8")

    def parse(self, path: Path, is_dependency: bool = False, **kwargs) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except Exception as e:
            return {"path": str(path), "error": str(e), "lang": self.language_name,
                    "functions": [], "classes": [], "imports": [], "variables": []}

        is_scss = path.suffix.lower() in (".scss", ".sass")

        # Try tree-sitter first if grammar is available
        if self.language and self.parser:
            try:
                tree = self.parser.parse(bytes(src, "utf8"))
                root = tree.root_node
                return self._parse_tree_sitter(root, str(path), is_dependency, is_scss, src)
            except Exception:
                pass

        # Fallback to regex-based parsing
        return self._parse_regex(str(path), src, is_dependency, is_scss)

    def _parse_tree_sitter(self, root, path: str, is_dependency: bool, is_scss: bool, src: str) -> Dict[str, Any]:
        """Tree-sitter based parsing for CSS/SCSS."""
        from src.core.parser.tree_sitter_manager import execute_query

        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []
        variables: List[Dict[str, Any]] = []
        function_calls: List[Dict[str, Any]] = []

        # CSS queries
        queries = {
            "imports": """
                (import_statement
                    (url) @url
                ) @import
            """,
            "at_rules": """
                (at_rule
                    name: (identifier) @name
                ) @at_rule
            """,
            "rules": """
                (rule_set
                    selectors: (_) @selector
                ) @rule
            """,
            "declarations": """
                (declaration
                    property: (property_name) @prop
                    value: (_) @val
                ) @decl
            """,
            "calls": """
                (call_expression
                    function: (function_name) @name
                ) @call_node
            """,
        }

        # Extract imports (@import, @use, @forward in SCSS)
        for node, tag in execute_query(self.language, queries["imports"], root):
            if tag == "import":
                line = node.start_point[0] + 1
                url_text = self._text(node).strip()
                imports.append({
                    "name": url_text,
                    "line_number": line,
                    "module": url_text,
                    "alias": None,
                })

        # Extract @-rules (@media, @keyframes, @supports, @mixin, @include, etc.)
        for node, tag in execute_query(self.language, queries["at_rules"], root):
            if tag == "name":
                rule_name = self._text(node).strip()
                parent = node.parent
                line = node.start_point[0] + 1
                end_line = parent.end_point[0] + 1 if parent else line
                functions.append({
                    "name": f"@{rule_name}",
                    "line_number": line,
                    "end_line": end_line,
                    "args": [],
                    "cyclomatic_complexity": 1,
                    "context": None,
                    "context_type": None,
                    "class_context": None,
                    "decorators": [],
                    "function_calls": [],
                    "lang": self.language_name,
                    "is_dependency": is_dependency,
                })

        # Extract rule sets (selectors) as classes
        for node, tag in execute_query(self.language, queries["rules"], root):
            if tag == "selector":
                selector_text = self._text(node).strip()
                line = node.start_point[0] + 1
                parent = node.parent
                end_line = parent.end_point[0] + 1 if parent else line
                classes.append({
                    "name": selector_text,
                    "line_number": line,
                    "end_line": end_line,
                    "bases": [],
                    "lang": self.language_name,
                    "is_dependency": is_dependency,
                })

        # Extract declarations as variables
        for node, tag in execute_query(self.language, queries["declarations"], root):
            if tag == "prop":
                prop_name = self._text(node).strip()
                line = node.start_point[0] + 1
                variables.append({
                    "name": prop_name,
                    "line_number": line,
                    "type": None,
                })

        for node, tag in execute_query(self.language, queries.get("calls", ""), root):
            if tag == "name":
                function_calls.append({
                    "name": self._text(node),
                    "line_number": node.start_point[0] + 1,
                    "lang": self.language_name,
                })

        return {
            "path": path,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "variables": variables,
            "function_calls": function_calls,
            "is_dependency": is_dependency,
            "lang": self.language_name,
        }

    def _parse_regex(self, path: str, src: str, is_dependency: bool, is_scss: bool) -> Dict[str, Any]:
        """Regex-based fallback parsing for CSS/SCSS."""
        lines = src.split("\n")

        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []
        variables: List[Dict[str, Any]] = []
        function_calls: List[Dict[str, Any]] = []

        # Patterns
        import_re = re.compile(r"^\s*@(?:import|use|forward)\s+(.+?);", re.IGNORECASE)
        at_rule_re = re.compile(r"^\s*(@[a-z-]+)\s*([^\{]*)", re.IGNORECASE)
        selector_re = re.compile(r"^\s*([^@\{]+)\{", re.IGNORECASE)
        prop_re = re.compile(r"^\s*([a-z-]+)\s*:", re.IGNORECASE)
        scss_var_re = re.compile(r"^\s*(\$[a-zA-Z_-][a-zA-Z0-9_-]*)\s*:", re.IGNORECASE)
        mixin_call_re = re.compile(r"@include\s+([a-zA-Z_-][a-zA-Z0-9_-]*)", re.IGNORECASE)
        extend_re = re.compile(r"@extend\s+([a-zA-Z_-][a-zA-Z0-9_-]*)", re.IGNORECASE)

        in_block = False
        block_depth = 0
        current_block_start = 0
        current_selector = ""

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Track block depth
            open_braces = stripped.count("{")
            close_braces = stripped.count("}")

            if not in_block and open_braces > 0:
                in_block = True
                block_depth = open_braces - close_braces
                current_block_start = i
                # Try to capture selector or at-rule
                before_brace = stripped.split("{")[0].strip()
                if before_brace.startswith("@"):
                    match = at_rule_re.match(stripped)
                    if match:
                        at_name = match.group(1).strip()
                        at_args = match.group(2).strip() if match.group(2) else ""
                        functions.append({
                            "name": f"{at_name} {at_args}" if at_args else at_name,
                            "line_number": i,
                            "end_line": i,  # will update on block close
                            "args": [],
                            "cyclomatic_complexity": 1,
                            "context": None,
                            "context_type": None,
                            "class_context": None,
                            "decorators": [],
                            "function_calls": [],
                            "lang": self.language_name,
                            "is_dependency": is_dependency,
                        })
                elif before_brace and not before_brace.startswith("//"):
                    current_selector = before_brace
                    classes.append({
                        "name": current_selector,
                        "line_number": i,
                        "end_line": i,
                        "bases": [],
                        "lang": self.language_name,
                        "is_dependency": is_dependency,
                    })
            elif in_block:
                block_depth += open_braces - close_braces
                if block_depth <= 0:
                    in_block = False
                    block_depth = 0
                    # Update end_line for the last class/function in this block
                    if classes and classes[-1]["end_line"] == classes[-1]["line_number"]:
                        classes[-1]["end_line"] = i
                    if functions and functions[-1]["end_line"] == functions[-1]["line_number"]:
                        functions[-1]["end_line"] = i
                    current_selector = ""
                else:
                    # Inside a block: capture properties, variables, calls
                    # Skip nested selectors in SCSS for simplicity (handled by next block start)
                    if "{" not in stripped:
                        prop_match = prop_re.match(stripped)
                        if prop_match:
                            variables.append({
                                "name": prop_match.group(1),
                                "line_number": i,
                                "type": None,
                            })

                        if is_scss:
                            scss_var_match = scss_var_re.match(stripped)
                            if scss_var_match:
                                variables.append({
                                    "name": scss_var_match.group(1),
                                    "line_number": i,
                                    "type": None,
                                })

                            for m in mixin_call_re.finditer(stripped):
                                function_calls.append({
                                    "name": m.group(1),
                                    "line_number": i,
                                })

            # Imports (can appear anywhere)
            import_match = import_re.match(stripped)
            if import_match:
                imports.append({
                    "name": import_match.group(1).strip().strip("'\""),
                    "line_number": i,
                    "module": import_match.group(1).strip().strip("'\""),
                    "alias": None,
                })

        return {
            "path": path,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "variables": variables,
            "function_calls": function_calls,
            "is_dependency": is_dependency,
            "lang": self.language_name,
        }
