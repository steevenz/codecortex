"""
Scope Resolution Pipeline — multi-pass cross-file reference resolution.
Ported from GitNexus's scope-resolution/ system.
Pipeline phases:
1. Scope Extraction — build scope tree from AST
2. Import Resolution — resolve cross-file imports
3. Local Binding — resolve references within same scope
4. Cross-File Binding — resolve references across files
5. Evidence Collection — gather evidence for each reference
6. Finalize — combine evidence to resolve ambiguous references.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Scope_resolution
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeIndex-v1.0
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger("CodeCortex.CodeIndex.ScopeResolution")

class ScopeKind(Enum):
    MODULE = "module"
    NAMESPACE = "namespace"
    CLASS = "class"
    FUNCTION = "function"
    BLOCK = "block"
    EXPRESSION = "expression"

@dataclass
class SourceRange:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

@dataclass
class ScopeNode:
    """A single scope in the hierarchy."""
    id: str
    kind: ScopeKind
    name: str
    file_path: str
    range: SourceRange
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    symbols: Dict[str, List[str]] = field(default_factory=dict)  # name -> [def_ids]

@dataclass
class SymbolDef:
    """A symbol definition (function, class, variable)."""
    id: str
    name: str
    kind: str  # 'function', 'class', 'variable', 'parameter'
    scope_id: str
    file_path: str
    range: SourceRange
    is_exported: bool = False
    full_name: Optional[str] = None
    type_info: Optional[str] = None

@dataclass
class Reference:
    """A reference to a symbol (usage site)."""
    id: str
    name: str
    file_path: str
    range: SourceRange
    scope_id: str
    resolved_def_id: Optional[str] = None
    confidence: float = 0.0  # 0.0 = unresolved, 1.0 = exact match
    evidence: List[str] = field(default_factory=list)

class ScopeTree:
    """
    Hierarchical scope tree for a single file.
    
    Maintains parent-child relationships between scopes
    and maps symbol names to their definitions within each scope.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.root: Optional[ScopeNode] = None
        self._nodes: Dict[str, ScopeNode] = {}
        self._symbols: Dict[str, SymbolDef] = {}
        self._references: Dict[str, Reference] = {}
        self._node_counter = 0
        self._sym_counter = 0
        self._ref_counter = 0
    
    def _next_id(self, prefix: str) -> str:
        self._node_counter += 1
        return f"{prefix}_{self.file_path}_{self._node_counter}"
    
    def add_scope(self, kind: ScopeKind, name: str, range: SourceRange,
                  parent_id: Optional[str] = None) -> str:
        sid = self._next_id("scope")
        node = ScopeNode(
            id=sid, kind=kind, name=name, file_path=self.file_path,
            range=range, parent_id=parent_id
        )
        self._nodes[sid] = node
        if parent_id and parent_id in self._nodes:
            self._nodes[parent_id].children.append(sid)
        if self.root is None:
            self.root = node
        return sid
    
    def add_symbol(self, name: str, kind: str, scope_id: str,
                   range: SourceRange, is_exported: bool = False) -> str:
        sid = self._next_id("sym")
        full_name = self._build_full_name(name, scope_id)
        sym = SymbolDef(
            id=sid, name=name, kind=kind, scope_id=scope_id,
            file_path=self.file_path, range=range,
            is_exported=is_exported, full_name=full_name
        )
        self._symbols[sid] = sym
        if scope_id in self._nodes:
            names = self._nodes[scope_id].symbols.setdefault(name, [])
            names.append(sid)
        return sid
    
    def add_reference(self, name: str, scope_id: str, range: SourceRange) -> str:
        rid = self._next_id("ref")
        ref = Reference(
            id=rid, name=name, file_path=self.file_path,
            range=range, scope_id=scope_id
        )
        self._references[rid] = ref
        return rid
    
    def _build_full_name(self, name: str, scope_id: str) -> str:
        parts = [name]
        seen = set()
        current = self._nodes.get(scope_id)
        while current:
            if current.id in seen:
                break
            seen.add(current.id)
            if current.kind in (ScopeKind.CLASS, ScopeKind.FUNCTION) and current.name:
                parts.insert(0, current.name)
            current = self._nodes.get(current.parent_id) if current.parent_id else None
        return ".".join(parts)
    
    def get_scope(self, scope_id: str) -> Optional[ScopeNode]:
        return self._nodes.get(scope_id)
    
    def get_symbol(self, sym_id: str) -> Optional[SymbolDef]:
        return self._symbols.get(sym_id)
    
    def get_reference(self, ref_id: str) -> Optional[Reference]:
        return self._references.get(ref_id)
    
    def lookup_in_scope(self, name: str, scope_id: str) -> List[str]:
        """Look up a symbol by name in a scope (walks up parent chain)."""
        current = self._nodes.get(scope_id)
        while current:
            if name in current.symbols:
                return current.symbols[name]
            if current.parent_id:
                current = self._nodes.get(current.parent_id)
            else:
                break
        return []
    
    def all_symbols(self) -> List[SymbolDef]:
        return list(self._symbols.values())
    
    def all_references(self) -> List[Reference]:
        return list(self._references.values())

    @property
    def symbol_count(self) -> int:
        return len(self._symbols)
    
    @property
    def reference_count(self) -> int:
        return len(self._references)

class WorkspaceIndex:
    """
    Cross-file index of all scopes, symbols, and imports.
    
    Maps:
    - Module name -> ScopeTree
    - Symbol name -> [(file_path, def_id)]
    - Import -> resolved target
    """
    
    def __init__(self):
        self._files: Dict[str, ScopeTree] = {}
        self._global_sym_index: Dict[str, List[Tuple[str, str]]] = {}
        self._import_map: Dict[str, Dict[str, str]] = {}  # file -> {imported_name -> target_file}
        self._export_index: Dict[str, List[Tuple[str, str, str]]] = {}  # file -> [(name, def_id, kind)]
    
    def add_file(self, tree: ScopeTree):
        self._files[tree.file_path] = tree
        for sym in tree.all_symbols():
            self._global_sym_index.setdefault(sym.name, []).append((tree.file_path, sym.id))
            if sym.is_exported:
                self._export_index.setdefault(tree.file_path, []).append(
                    (sym.name, sym.id, sym.kind)
                )
    
    def register_import(self, source_file: str, imported_name: str, target_file: str):
        self._import_map.setdefault(source_file, {})[imported_name] = target_file
    
    def resolve_name(self, name: str, file_path: str) -> List[Tuple[str, str, float]]:
        """
        Resolve a name to (file_path, def_id, confidence) tuples.
        Checks: local scope -> imports -> global index.
        """
        results: List[Tuple[str, str, float]] = []
        
        # 1. Check local scope
        tree = self._files.get(file_path)
        if tree and tree.root:
            ids = tree.lookup_in_scope(name, tree.root.id)
            for sid in ids:
                results.append((file_path, sid, 1.0))
        
        # 2. Check imports
        if file_path in self._import_map and name in self._import_map[file_path]:
            target = self._import_map[file_path][name]
            results.append((target, "", 0.8))
        
        # 3. Check global index
        if name in self._global_sym_index:
            for fp, sid in self._global_sym_index[name]:
                if fp != file_path:
                    results.append((fp, sid, 0.6))
        
        return results
    
    def get_exported_symbols(self, file_path: str) -> List[Tuple[str, str, str]]:
        return self._export_index.get(file_path, [])
    
    @property
    def file_count(self) -> int:
        return len(self._files)
    
    @property
    def total_symbols(self) -> int:
        return sum(t.symbol_count for t in self._files.values())
    
    @property
    def total_references(self) -> int:
        return sum(t.reference_count for t in self._files.values())

class ScopeExtractor:
    """
    Phase 1: Extract scopes and symbols from parsed files.
    
    Processes TreeSitter parse results and builds ScopeTree for each file.
    """
    
    def _parsed_to_symbols(self, file_path: str, parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert tree-sitter flat parsed data to hierarchical symbol list."""
        symbols = parsed.get("symbols", [])
        if symbols:
            return symbols

        class_names = {}
        for cls in parsed.get("classes", []):
            cls_name = cls["name"]
            class_code_ref = f"{file_path}:class:{cls_name}@{cls.get('line_number', 1)}"
            class_sym = {
                "type": "class",
                "name": cls_name,
                "start_line": cls.get("line_number", 1),
                "end_line": cls.get("end_line", cls.get("line_number", 1)),
                "is_exported": False,
                "children": [],
                "code_ref": class_code_ref,
            }
            class_names[cls_name] = class_sym
            symbols.append(class_sym)

        for fn in parsed.get("functions", []):
            fn_name = fn["name"]
            class_ctx = fn.get("class_context") or (fn.get("context") if fn.get("context_type") == "class" else None)
            sym_type = "method" if class_ctx else "function"
            sym = {
                "type": sym_type,
                "name": fn_name,
                "start_line": fn.get("line_number", 1),
                "end_line": fn.get("end_line", fn.get("line_number", 1)),
                "is_exported": False,
                "children": [],
            }
            if class_ctx and class_ctx in class_names:
                class_names[class_ctx].setdefault("children", []).append(sym)
            else:
                symbols.append(sym)

        for var in parsed.get("variables", []):
            symbols.append({
                "type": "variable",
                "name": var["name"],
                "start_line": var.get("line_number", 1),
                "end_line": var.get("line_number", 1),
                "is_exported": False,
                "children": [],
            })

        return symbols

    def build_scope_tree(self, file_path: str, parsed: Dict[str, Any]) -> ScopeTree:
        """Build a scope tree from TreeSitter parse results."""
        tree = ScopeTree(file_path)
        symbols = self._parsed_to_symbols(file_path, parsed)
        module_id = tree.add_scope(
            ScopeKind.MODULE, Path(file_path).stem,
            SourceRange(1, 0, 100, 0)
        )
        
        for sym in symbols:
            scope_id = module_id
            sym_type = sym.get("type", "unknown")
            sym_name = sym.get("name", "")
            sym_range = SourceRange(
                sym.get("start_line", 1), 0,
                sym.get("end_line", 1), 0
            )
            
            if sym_type in ("class", "function", "method"):
                child_id = tree.add_scope(
                    ScopeKind.CLASS if sym_type == "class" else ScopeKind.FUNCTION,
                    sym_name, sym_range, parent_id=module_id
                )
                tree.add_symbol(sym_name, sym_type, child_id, sym_range,
                                is_exported=sym.get("is_exported", False))
                for child in sym.get("children", []):
                    crange = SourceRange(child.get("start_line", 1), 0, child.get("end_line", 1), 0)
                    tree.add_symbol(child.get("name", ""), child.get("type", "method"), child_id, crange)
            else:
                tree.add_symbol(sym_name, sym_type, scope_id, sym_range)
        
        return tree

class ReferenceResolver:
    """
    Multi-pass reference resolver.
    
    Pass 1: Resolve local references (within same file)
    Pass 2: Resolve cross-file references (via imports)
    Pass 3: Resolve by name matching (global index fallback)
    """
    
    def __init__(self, workspace: WorkspaceIndex):
        self.workspace = workspace
        self.resolved_count = 0
        self.unresolved_count = 0
    
    def resolve_all(self) -> Dict[str, int]:
        """Run all resolution passes. Returns stats."""
        total = 0
        for file_path, tree in self.workspace._files.items():
            for ref in tree.all_references():
                resolved = self._resolve_single(ref, file_path)
                if resolved:
                    self.resolved_count += 1
                else:
                    self.unresolved_count += 1
                total += 1
        
        return {
            "total_references": total,
            "resolved": self.resolved_count,
            "unresolved": self.unresolved_count,
            "resolution_rate": round(self.resolved_count / max(total, 1) * 100, 1)
        }
    
    def _resolve_single(self, ref: Reference, file_path: str) -> bool:
        """Attempt to resolve a single reference through multiple passes."""
        # Pass 1: Local scope resolution
        tree = self.workspace._files.get(file_path)
        if tree:
            local_defs = tree.lookup_in_scope(ref.name, ref.scope_id)
            if local_defs:
                ref.resolved_def_id = local_defs[0]
                ref.confidence = 1.0
                ref.evidence.append("local_scope")
                return True
        
        # Pass 2: Import resolution
        candidates = self.workspace.resolve_name(ref.name, file_path)
        for fp, sid, confidence in candidates:
            if confidence > ref.confidence:
                ref.resolved_def_id = sid if sid else f"{fp}::{ref.name}"
                ref.confidence = confidence
                ref.evidence.append(f"cross_file:{fp}")
                return True
        
        return False

def build_workspace_index(files: List[Dict[str, Any]]) -> WorkspaceIndex:
    """
    Build a complete workspace index from parsed files.
    
    Each file dict should have: path, language, parsed (result from TreeSitterParser.parse)
    """
    extractor = ScopeExtractor()
    workspace = WorkspaceIndex()
    
    for f in files:
        file_path = f.get("path", "")
        parsed = f.get("parsed", {})
        if parsed:
            tree = extractor.build_scope_tree(file_path, parsed)
            workspace.add_file(tree)
            logger.info(f"Scope tree built: {file_path} ({tree.symbol_count} symbols)")
    
    return workspace

def resolve_workspace_references(workspace: WorkspaceIndex) -> Dict[str, int]:
    """Run full scope resolution on a workspace."""
    resolver = ReferenceResolver(workspace)
    stats = resolver.resolve_all()
    logger.info(f"Scope resolution complete: {stats}")
    return stats
