# CodeGraph: MCP Tools

> **Source:** `src/domain/codegraph/api/tools.py`

## Tool Reference

### `graph_find_symbols`

Find symbols (functions, classes, variables) by name across the codebase.

```
Parameters:
  search_term (str)       — Symbol name to search for
  symbol_type (str)       — "function" | "class" | "variable" | "any" (default: "any")
  repo_path (str?)        — Scope to specific repository
  fuzzy_search (bool)     — Enable approximate name matching (default: False)
  edit_distance (int)     — Max edit distance for fuzzy search (default: 2)
  limit (int)             — Max results (default: 20)

Returns:
  functions[], classes[], variables[], total
```

---

### `graph_query`

Query code relationships in the graph by relation type.

```
Parameters:
  query_type (str) — See relationship types below
  target (str)     — Symbol or module name
  context (str?)   — File path to disambiguate
  repo_path (str?) — Scope to repository
  limit (int)      — Max results (default: 20)

Query Types:
  "callers"       — Who calls target function
  "callees"       — What target function calls
  "all_callers"   — Deep recursive callers
  "all_callees"   — Deep recursive callees
  "imports"       — Files that import the target
  "modifies"      — What modifies target variable/state
  "hierarchy"     — Parent and child classes
  "overrides"     — Methods that override target
  "chain"         — Call chain from target
  "deps"          — Module dependencies
  "complexity"    — Cyclomatic complexity
  "dead_code"     — Unused functions in scope
```

---

### `graph_trace_flow`

Recursively trace call graph from a start symbol to identify execution flow.

```
Parameters:
  start_symbol_id (str) — Graph node ID (from graph_find_symbols)
  max_depth (int)       — Max recursion depth (default: 5)

Returns:
  Hierarchical call tree
```

---

### `graph_build`

Build (or rebuild) the full code relationship graph for a repository.

```
Parameters:
  repo_id (str)        — Repository UUID
  repo_path (str)      — Absolute path to repo root
  include_stats (bool) — Include node/edge counts (default: True)

Returns:
  build stats + optional graph statistics
```

---

### `arch_analyze`

Run a full architectural analysis: coupling, god nodes, security, community.

```
Parameters:
  repo_id (str?)    — Repository UUID
  path (str?)       — Absolute path (for on-demand)
  include_summary (bool) — Generate Markdown narrative (default: True)

Returns:
  Architectural metrics + optional Markdown summary
```

---

### `arch_audit`

Audit for specific architectural smells.

```
Parameters:
  repo_id (str)        — Repository UUID
  audit_type (str)     — "god_nodes" | "security" | "dead_code" | "complexity" | "all"
  threshold (int)      — Min in-degree for god nodes (default: 10)
  limit (int)          — Max results per category (default: 50)
  repo_path (str?)     — Scope to specific path

Returns:
  Findings organized by type with severity levels
```

---

## Tool Count

| Domain | Tool Count |
|--------|-----------|
| CodeGraph | 7 (graph_find_symbols, graph_query, graph_find_related, graph_build, graph_trace_flow, arch_analyze, arch_audit) |
