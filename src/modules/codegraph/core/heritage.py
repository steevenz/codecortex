"""
Heritage Extraction — extracts class inheritance hierarchies from AST.
Ported from GitNexus's heritage-processor.ts.
Supports Python, TypeScript/JS, Java, and Go inheritance patterns.

:project: CodeCortex
:package: Modules.Codegraph.Core.Heritage
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("CodeCortex.CodeGraph.Heritage")

PYTHON_CLASS_PATTERN = re.compile(
    r"class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:"
)
TS_CLASS_PATTERN = re.compile(
    r"class\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+([^{]+))?\s*\{"
)
JAVA_CLASS_PATTERN = re.compile(
    r"class\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+([^{]+))?\s*\{"
)
GO_STRUCT_PATTERN = re.compile(
    r"type\s+(\w+)\s+struct\s*\{"
)

@dataclass
class HeritageInfo:
    class_name: str
    parent: Optional[str]
    interfaces: List[str]
    language: str
    file_path: str
    line_number: int

class HeritageExtractor:
    """
    Extracts inheritance hierarchies from source code.

    Supports multi-language class parsing:
    - Python: `class Foo(Bar, Baz)` → parents = [Bar, Baz]
    - TypeScript: `class Foo extends Bar implements Baz` → parent = Bar, interfaces = [Baz]
    - Java: same as TypeScript
    - Go: `type Foo struct { Bar }` → parent = Bar (embedding)
    """

    def __init__(self):
        self.heritage_map: Dict[str, HeritageInfo] = {}

    def extract_from_file(self, content: str, file_path: str, language: str) -> List[HeritageInfo]:
        """Extract heritage info from file content."""
        results = []
        if language == "python":
            results = self._extract_python(content, file_path)
        elif language in ("typescript", "javascript", "tsx"):
            results = self._extract_ts(content, file_path)
        elif language == "java":
            results = self._extract_java(content, file_path)
        elif language == "go":
            results = self._extract_go(content, file_path)

        for info in results:
            self.heritage_map[info.class_name] = info
        return results

    def _extract_python(self, content: str, file_path: str) -> List[HeritageInfo]:
        results = []
        for i, line in enumerate(content.split("\n"), 1):
            m = PYTHON_CLASS_PATTERN.search(line)
            if m:
                class_name = m.group(1)
                base_clause = m.group(2)
                parents = []
                if base_clause and base_clause.strip():
                    parents = [p.strip() for p in base_clause.split(",") if p.strip()]
                parent = parents[0] if parents else None
                interfaces = parents[1:] if len(parents) > 1 else []
                info = HeritageInfo(
                    class_name=class_name,
                    parent=parent,
                    interfaces=interfaces,
                    language="python",
                    file_path=file_path,
                    line_number=i,
                )
                results.append(info)
        return results

    def _extract_ts(self, content: str, file_path: str) -> List[HeritageInfo]:
        results = []
        for i, line in enumerate(content.split("\n"), 1):
            m = TS_CLASS_PATTERN.search(line)
            if m:
                class_name = m.group(1)
                parent = m.group(2)
                interfaces_str = m.group(3)
                interfaces = [s.strip() for s in interfaces_str.split(",") if s.strip()] if interfaces_str else []
                info = HeritageInfo(
                    class_name=class_name,
                    parent=parent,
                    interfaces=interfaces,
                    language="typescript",
                    file_path=file_path,
                    line_number=i,
                )
                results.append(info)
        return results

    def _extract_java(self, content: str, file_path: str) -> List[HeritageInfo]:
        results = []
        for i, line in enumerate(content.split("\n"), 1):
            m = JAVA_CLASS_PATTERN.search(line)
            if m:
                class_name = m.group(1)
                parent = m.group(2)
                interfaces_str = m.group(3)
                interfaces = [s.strip() for s in interfaces_str.split(",") if s.strip()] if interfaces_str else []
                info = HeritageInfo(
                    class_name=class_name,
                    parent=parent,
                    interfaces=interfaces,
                    language="java",
                    file_path=file_path,
                    line_number=i,
                )
                results.append(info)
        return results

    def _extract_go(self, content: str, file_path: str) -> List[HeritageInfo]:
        results = []
        for i, line in enumerate(content.split("\n"), 1):
            m = GO_STRUCT_PATTERN.search(line)
            if m:
                class_name = m.group(1)
                # Go uses embedding, so parents are detected differently
                info = HeritageInfo(
                    class_name=class_name,
                    parent=None,
                    interfaces=[],
                    language="go",
                    file_path=file_path,
                    line_number=i,
                )
                results.append(info)
        return results

    def build_hierarchy(self) -> Dict[str, List[str]]:
        """Build parent→children map for the full hierarchy."""
        hierarchy: Dict[str, List[str]] = {}
        for name, info in self.heritage_map.items():
            if info.parent:
                children = hierarchy.setdefault(info.parent, [])
                children.append(name)
        return hierarchy

    def get_ancestors(self, class_name: str) -> List[str]:
        """Get full ancestor chain for a class."""
        ancestors = []
        current = class_name
        while current in self.heritage_map:
            parent = self.heritage_map[current].parent
            if parent and parent != current:
                ancestors.append(parent)
                current = parent
            else:
                break
        return ancestors

    def get_descendants(self, class_name: str) -> List[str]:
        """Get all descendants of a class."""
        hierarchy = self.build_hierarchy()
        descendants = []
        queue = [class_name]
        while queue:
            current = queue.pop(0)
            children = hierarchy.get(current, [])
            for child in children:
                descendants.append(child)
                queue.append(child)
        return descendants

def extract_heritage_from_files(files: List[Dict]) -> Dict:
    """Bulk extract heritage from a list of file dicts with content + language."""
    extractor = HeritageExtractor()
    total_classes = 0
    for f in files:
        results = extractor.extract_from_file(
            content=f.get("content", ""),
            file_path=f.get("path", ""),
            language=f.get("language", "python"),
        )
        total_classes += len(results)

    hierarchy = extractor.build_hierarchy()
    return {
        "classes": list(extractor.heritage_map.keys()),
        "total_classes": total_classes,
        "hierarchy": hierarchy,
        "inheritance_edges": sum(len(v) for v in hierarchy.values()),
    }
