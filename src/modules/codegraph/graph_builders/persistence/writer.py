"""
GraphWriter — persists nodes and relationships to the graph backend.

:project: CodeCortex
:package: Modules.Codegraph.Graph_builders.Persistence.Writer
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from src.core.graph import GraphManager
from src.core.logging import get_logger

logger = get_logger("CodeCortex.Domain.CodeGraph.Persistence")

_LABEL_WHITELIST: frozenset[str] = frozenset({
    "Repository", "File", "Function", "Class",
    "Interface", "Module", "Struct", "Enum",
})
_REL_WHITELIST: frozenset[str] = frozenset({
    "CONTAINS", "CALLS", "INHERITS", "IMPLEMENTS", "IMPORTS",
})

# Match field per node label (used in batch UNWIND queries)
_NODE_KEY: Dict[str, str] = {
    "Repository": "path",
    "File":       "path",
    "Function":   "name",
    "Class":      "name",
    "Interface":  "name",
    "Module":     "name",
    "Struct":     "name",
    "Enum":       "name",
}
# Whether a label needs both name+path to uniquely identify a node
_NODE_NEEDS_PATH: frozenset[str] = frozenset({"Function", "Class", "Interface", "Module", "Struct", "Enum"})

# Whitelist of allowed node property names used in MATCH clauses (Cypher injection guard)
_PROP_WHITELIST: frozenset[str] = frozenset({
    "path", "name", "uid", "relative_path",
})

class GraphWriter:
    def __init__(self, gm: Optional[GraphManager] = None):
        self.gm = gm or GraphManager()

    def _run(self, q: str, **p) -> Any:
        b = self.gm.get_backend()
        with b.get_session() as s:
            return s.run(q, **p)

    @staticmethod
    def _label(name: str) -> str:
        if name not in _LABEL_WHITELIST:
            raise ValueError(f"Invalid Cypher label: {name}")
        return name

    @staticmethod
    def _rel(name: str) -> str:
        if name not in _REL_WHITELIST:
            raise ValueError(f"Invalid Cypher relationship type: {name}")
        return name

    @staticmethod
    def _prop(name: str) -> str:
        if name not in _PROP_WHITELIST:
            raise ValueError(f"Invalid Cypher property key: {name}")
        return name

    # -------------------------------------------------------------------------
    # Node upsert helpers
    # -------------------------------------------------------------------------

    def merge_repo(self, path: str, name: str, indexed_at: str, commit: str = "", dep: bool = False) -> str:
        r = self._run(
            "MERGE (n:Repository {path:$p}) "
            "ON CREATE SET n.name=$n,n.is_dependency=$d,n.indexed_at=$i,n.commit_hash=$c "
            "ON MATCH SET n.indexed_at=$i,n.commit_hash=$c "
            "RETURN n.path AS id",
            p=path, n=name, d=dep, i=indexed_at, c=commit,
        )
        return (r.single() or {}).get("id", path)

    def merge_file(self, path: str, name: str, rel: str, repo: str, dep: bool = False) -> str:
        r = self._run(
            "MERGE (f:File {path:$p}) "
            "ON CREATE SET f.name=$n,f.relative_path=$r,f.is_dependency=$d "
            "WITH f MATCH (repo:Repository {path:$rp}) MERGE (repo)-[:CONTAINS]->(f) "
            "RETURN f.path AS id",
            p=path, n=name, r=rel, d=dep, rp=repo,
        )
        return (r.single() or {}).get("id", path)

    def merge_fn(self, fn: Dict[str, Any]) -> str:
        uid = fn.get("uid") or f"fn:{fn['path']}:{fn['name']}:{fn['line_number']}"
        r = self._run(
            "MERGE (n:Function {uid:$uid}) "
            "ON CREATE SET n.name=$n,n.path=$p,n.line_number=$l,n.end_line=$e,"
            "n.source=$s,n.docstring=$d,n.lang=$g,n.cyclomatic_complexity=$cc,"
            "n.context=$ctx,n.context_type=$ct,n.class_context=$ccx,"
            "n.is_dependency=$dep,n.decorators=$dec,n.args=$a "
            "ON MATCH SET n.name=$n,n.path=$p,n.line_number=$l,n.end_line=$e,"
            "n.source=$s,n.docstring=$d,n.lang=$g,n.cyclomatic_complexity=$cc,"
            "n.context=$ctx,n.context_type=$ct,n.class_context=$ccx,"
            "n.is_dependency=$dep,n.decorators=$dec,n.args=$a "
            "RETURN n.uid AS id",
            uid=uid, n=fn["name"], p=fn["path"],
            l=fn["line_number"], e=fn.get("end_line", fn["line_number"]),
            s=fn.get("source", ""), d=fn.get("docstring", ""),
            g=fn.get("lang", ""), cc=fn.get("cyclomatic_complexity", 1),
            ctx=fn.get("context", ""), ct=fn.get("context_type", ""),
            ccx=fn.get("class_context", ""), dep=fn.get("is_dependency", False),
            dec=fn.get("decorators", []), a=fn.get("args", []),
        )
        return (r.single() or {}).get("id", uid)

    def merge_cls(self, cls: Dict[str, Any]) -> str:
        uid = cls.get("uid") or f"cls:{cls['path']}:{cls['name']}:{cls['line_number']}"
        r = self._run(
            "MERGE (n:Class {uid:$uid}) "
            "ON CREATE SET n.name=$n,n.path=$p,n.line_number=$l,n.end_line=$e,"
            "n.source=$s,n.docstring=$d,n.lang=$g,n.is_dependency=$dep,n.decorators=$dec "
            "ON MATCH SET n.name=$n,n.path=$p,n.line_number=$l,n.end_line=$e,"
            "n.source=$s,n.docstring=$d,n.lang=$g,n.is_dependency=$dep,n.decorators=$dec "
            "RETURN n.uid AS id",
            uid=uid, n=cls["name"], p=cls["path"],
            l=cls["line_number"], e=cls.get("end_line", cls["line_number"]),
            s=cls.get("source", ""), d=cls.get("docstring", ""),
            g=cls.get("lang", ""), dep=cls.get("is_dependency", False),
            dec=cls.get("decorators", []),
        )
        return (r.single() or {}).get("id", uid)

    def link_contains(self, pl: str, pf: str, pv: str, cl: str, cf: str, cv: str) -> None:
        q = (
            f"MATCH (p:{self._label(pl)} {{{self._prop(pf)}:$pv}}) "
            f"MATCH (c:{self._label(cl)} {{{self._prop(cf)}:$cv}}) "
            f"MERGE (p)-[:{self._rel('CONTAINS')}]->(c)"
        )
        self._run(q, pv=pv, cv=cv)

    # -------------------------------------------------------------------------
    # Single-item relationship writes (kept for compatibility / small writes)
    # -------------------------------------------------------------------------

    def link_calls(
        self,
        caller_l: str, caller_f: str, caller_v: str,
        callee_l: str, callee_f: str, callee_v: str,
        line: int = 0, args: Optional[List[str]] = None, full: str = "",
    ) -> None:
        q = (
            f"MATCH (caller:{self._label(caller_l)} {{{self._prop(caller_f)}:$cv}}) "
            f"MATCH (callee:{self._label(callee_l)} {{{self._prop(callee_f)}:$cv2}}) "
            f"MERGE (caller)-[:{self._rel('CALLS')} {{line_number:$l,args:$a,full_call_name:$f}}]->(callee)"
        )
        self._run(q, cv=caller_v, cv2=callee_v, l=line, a=args or [], f=full)

    def link_inherits(self, child: str, parent: str) -> None:
        self._run(
            "MATCH (c:Class {uid:$child}) MATCH (p:Class {uid:$parent}) MERGE (c)-[:INHERITS]->(p)",
            child=child, parent=parent,
        )

    # -------------------------------------------------------------------------
    # Batch write methods — use UNWIND for O(1) round-trips regardless of size
    # -------------------------------------------------------------------------

    def write_calls_batch(
        self,
        caller_label: str,
        callee_label: str,
        items: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> None:
        """
        Batch-write CALLS edges. items must have keys:
          caller_name, caller_path, callee_name, callee_path, line_number, full_call_name
        File nodes are matched by path only; Function/Class by name+path.
        """
        if not items:
            return
        cl = self._label(caller_label)
        ce = self._label(callee_label)

        if caller_label == "File":
            caller_match = "{path: row.caller_path}"
        else:
            caller_match = "{name: row.caller_name, path: row.caller_path}"

        if callee_label == "File":
            callee_match = "{path: row.callee_path}"
        else:
            callee_match = "{name: row.callee_name, path: row.callee_path}"

        q = (
            f"UNWIND $batch AS row "
            f"MATCH (caller:{cl} {caller_match}) "
            f"MATCH (callee:{ce} {callee_match}) "
            f"MERGE (caller)-[:CALLS {{line_number: row.line_number, full_call_name: row.full_call_name}}]->(callee)"
        )
        b = self.gm.get_backend()
        with b.get_session() as s:
            for i in range(0, len(items), batch_size):
                s.run(q, batch=items[i:i + batch_size])

    def write_inherits_batch(
        self,
        items: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> None:
        """
        Batch-write INHERITS edges. items must have keys:
          child_name, child_path, parent_name, parent_path
        """
        if not items:
            return
        q = (
            "UNWIND $batch AS row "
            "MATCH (c:Class {name: row.child_name, path: row.child_path}) "
            "MATCH (p:Class {name: row.parent_name, path: row.parent_path}) "
            "MERGE (c)-[:INHERITS]->(p)"
        )
        b = self.gm.get_backend()
        with b.get_session() as s:
            for i in range(0, len(items), batch_size):
                s.run(q, batch=items[i:i + batch_size])
