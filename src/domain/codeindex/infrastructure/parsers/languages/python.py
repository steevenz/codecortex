"""Python tree-sitter parser — stub. Full port from legacy in progress."""
import ast, os, tempfile, logging, warnings
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.core.utils.debug_log import info_logger, error_logger, warning_logger
from src.core.tree_sitter_manager import execute_query
logging.getLogger("traitlets").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", message=".*IPython is needed.*")

PY_QUERIES = {
    "imports": "(import_statement name: (_) @import) (import_from_statement) @from",
    "classes": "(class_definition name: (identifier) @name superclasses: (argument_list)? @sup body: (block) @body)",
    "functions": "(function_definition name: (identifier) @name parameters: (parameters) @params body: (block) @body)",
    "calls": "(call function: (identifier) @name) (call function: (attribute attribute: (identifier) @name) @full)",
    "variables": "(assignment left: (identifier) @name)",
}

class PythonTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper
        self.language_name = wrapper.language_name
        self.language = wrapper.language
        self.parser = wrapper.parser

    def _text(self, node) -> str:
        return node.text.decode("utf-8")

    def parse(self, path: Path, is_dependency: bool = False, is_notebook: bool = False, index_source: bool = False) -> Dict[str, Any]:
        orig = path; tmp = None; self.index_source = index_source
        try:
            if is_notebook:
                try:
                    import nbformat
                    from nbconvert import PythonExporter
                except Exception:
                    return {"path": str(orig), "error": "notebook_support_unavailable"}
                with open(path, "r", encoding="utf-8") as f: nb = nbformat.read(f, as_version=4)
                code, _ = PythonExporter().from_notebook_node(nb)
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py", encoding="utf-8") as tf:
                    tf.write(code); tmp = Path(tf.name); path = tmp
            with open(path, "r", encoding="utf-8") as f: src = f.read()
            tree = self.parser.parse(bytes(src, "utf8")); root = tree.root_node
            return {"path": str(orig), "functions": self._funcs(root), "classes": self._classes(root),
                    "variables": self._vars(root), "imports": self._imports(root),
                    "function_calls": self._calls(root), "is_dependency": is_dependency, "lang": self.language_name}
        except Exception as e:
            error_logger(f"Parse failed {orig}: {e}"); return {"path": str(orig), "error": str(e)}
        finally:
            if tmp and tmp.exists(): os.remove(tmp)

    def _funcs(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, PY_QUERIES["functions"], root):
            if tag == "name":
                fn = n.parent
                params = fn.child_by_field_name("parameters")
                body = fn.child_by_field_name("body")
                decos = [self._text(c) for c in fn.children if c.type == "decorator"]
                calls = self._calls(body or fn)
                out.append({"name": self._text(n), "line_number": n.start_point[0]+1,
                            "end_line": fn.end_point[0]+1,
                            "args": [self._text(p) for p in (params.children if params else []) if p.type == "identifier"] if params else [],
                            "cyclomatic_complexity": 1, "context": None, "context_type": None,
                            "class_context": None, "decorators": decos,
                            "function_calls": calls,
                            "lang": self.language_name, "is_dependency": False})
        return out

    def _classes(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, PY_QUERIES["classes"], root):
            if tag == "name":
                cn = n.parent; sup = cn.child_by_field_name("superclasses")
                bases = [self._text(c) for c in (sup.children if sup else []) if c.type not in (",", "(", ")")]
                out.append({"name": self._text(n), "line_number": n.start_point[0]+1,
                            "end_line": cn.end_point[0]+1, "bases": bases,
                            "lang": self.language_name, "is_dependency": False})
        return out

    def _imports(self, root) -> List[Dict[str, Any]]:
        out = []; seen = set()
        for n, tag in execute_query(self.language, PY_QUERIES["imports"], root):
            if tag == "import":
                imp = n.parent
                if imp.type in ("import_statement", "aliased_import"):
                    name = self._text(n)
                    if name not in seen: seen.add(name); out.append({"name": name, "full_import_name": name, "line_number": imp.start_point[0]+1, "alias": None, "lang": self.language_name, "is_dependency": False})
            elif tag == "from":
                fi = n; mod = fi.child_by_field_name("module_name")
                if mod:
                    mod_name = self._text(mod)
                    for c in fi.children:
                        if c.type in ("identifier", "dotted_name"):
                            full = f"{mod_name}.{self._text(c)}"
                            if full not in seen: seen.add(full); out.append({"name": self._text(c), "full_import_name": full, "line_number": fi.start_point[0]+1, "alias": None, "lang": self.language_name, "is_dependency": False})
        return out

    def _calls(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, PY_QUERIES["calls"], root):
            if tag == "name":
                call_node = n.parent if n.parent.type == "call" else n.parent.parent
                full = call_node.child_by_field_name("function")
                args = []
                an = call_node.child_by_field_name("arguments")
                if an:
                    for a in an.children:
                        t = self._text(a)
                        if t and t not in ("(", ")", ","): args.append(t)
                out.append({"name": self._text(n), "full_name": self._text(full) if full else self._text(n),
                            "line_number": n.start_point[0]+1, "args": args,
                            "inferred_obj_type": None, "context": None,
                            "class_context": None, "lang": self.language_name, "is_dependency": False})
        return out

    def _vars(self, root) -> List[Dict[str, Any]]:
        out = []
        for n, tag in execute_query(self.language, PY_QUERIES["variables"], root):
            if tag == "name":
                asn = n.parent
                right = asn.child_by_field_name("right")
                out.append({"name": self._text(n), "line_number": n.start_point[0]+1,
                            "value": self._text(right) if right else None,
                            "context": None, "lang": self.language_name, "is_dependency": False})
        return out


def pre_scan_python(files: List[Path], parser_wrapper) -> Dict[str, List[str]]:
    imports_map = {}
    q = "(class_definition name: (identifier) @name) (function_definition name: (identifier) @name)"
    for path in files:
        tmp = None
        try:
            src = ""
            if path.suffix == ".ipynb":
                with open(path, "r", encoding="utf-8") as f: nb = nbformat.read(f, as_version=4)
                code, _ = PythonExporter().from_notebook_node(nb)
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py", encoding="utf-8") as tf:
                    tf.write(code); tmp = Path(tf.name)
                with open(tmp, "r", encoding="utf-8") as f: src = f.read()
            else:
                with open(path, "r", encoding="utf-8") as f: src = f.read()
            tree = parser_wrapper.parser.parse(bytes(src, "utf8"))
            for cap, _ in execute_query(parser_wrapper.language, q, tree.root_node):
                name = cap.text.decode("utf-8")
                imports_map.setdefault(name, []).append(str(path.resolve()))
        except Exception as e:
            warning_logger(f"Pre-scan failed {path}: {e}")
        finally:
            if tmp and tmp.exists(): os.remove(tmp)
    return imports_map
