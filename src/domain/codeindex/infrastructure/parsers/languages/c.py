"""C tree-sitter parser — stub."""
from pathlib import Path
from typing import Any, Dict

class CTreeSitterParser:
    def __init__(self, wrapper: Any):
        self.wrapper = wrapper; self.language_name = wrapper.language_name
        self.language = wrapper.language; self.parser = wrapper.parser
    def parse(self, path: Path, is_dependency: bool = False, **kwargs) -> Dict[str, Any]:
        return {"path": str(path), "error": "parser_not_implemented", "lang": self.language_name, "functions": [], "classes": [], "imports": [], "variables": []}
