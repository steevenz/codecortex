# CodeGraph: MCP Tools

> **Source:** `src/modules/codegraph/api/tools.py`

## Tool Reference

### `graph_search`

Unified search tool for finding symbols, tracing relations, semantic search, and modular structure analysis.

```
Parameters:
  action (str)              — "symbol" | "relation" | "trace_flow" | "modular" | "semantic"
  fields (list[str]?)       — Return only these top-level result keys (e.g. ["functions"]) — reduces token consumption
  query (str?)              — Search keyword (for symbol, relation, semantic actions)
  repo_id (str?)            — Repository UUID (required for relation/trace_flow/modular)
  repo_path (str?)          — Path to scope search (for symbol/semantic actions)
  symbol_type (str)         — "function" | "class" | "variable" | "any" (default: "any")
  fuzzy (bool)              — Enable fuzzy/typo-tolerant name matching (default: False)
  edit_distance (int)       — Max edit distance for fuzzy search (default: 2)
  relation_type (str?)      — Relation subtype: "callers", "callees", "imports", "overrides", "hierarchy", "modifies", "deps"
  target_symbol_id (str?)   — Graph node ID for trace_flow action
  max_depth (int)           — Traversal depth for relation/trace_flow (default: 3, max: 10)
  modular_type (str?)       — Filter by "module" | "plugin" | "widget" | "component" | "core" | "service"
  limit (int)               — Max results (default: 20, max: 200)
  cursor (str?)             — Pagination cursor for large result sets

Actions:
  "symbol"      — Find functions/classes/variables by name (fuzzy supported)
  "relation"    — Find callers, callees, imports, hierarchy, overrides
  "trace_flow"  — Trace execution path from a symbol
  "modular"     — List modules, plugins, widgets, components
  "semantic"    — Natural-language search for related code

Returns:
  action-specific results (functions/classes/variables arrays, relationship lists, call trees, etc.)
```

---

### `graph_query`

Query code relationships: callers, callees, hierarchy, trace path, and more.

```
Parameters:
  query_type (str)         — Relationship type to query
  target (str)             — Symbol name (use "module::function" to disambiguate)
  repo_id (str?)           — Repository UUID (required for trace_path/trace_flow/visualize)
  repo_path (str?)         — Optional path to scope SQLite-backed queries
  max_depth (int)          — Max traversal depth for recursive queries (default: 3, max: 10)
  end_node (str?)          — Target end symbol for trace_path query
  context (str?)           — Optional file path to disambiguate symbol name
  direction (str)          — "inbound" | "outbound" | "both" (default: "both")
  limit (int)              — Max results (default: 20)
  viz_format (str)         — Visualization format for query_type="visualize": "mermaid" | "dot" (default: "mermaid")
  fields (list[str]?)      — Return only these top-level result keys — reduces token consumption

Query Types:
  "callers"/"callees"         → Direct callers/callees of target
  "all_callers"/"all_callees" → Recursive deep callers/callees
  "trace_path"                → Shortest path between target and end_node
  "imports"                   → Files that import the target module
  "hierarchy"                 → Parent/child classes of target
  "overrides"                 → Methods that override target
  "chain"                     → Call chain from target
  "deps"                      → Module dependencies
  "complexity"                → Cyclomatic complexity
  "dead_code"                 → Unused functions in scope
  "trace_flow"                → Full execution flow from target
  "visualize"                 → Render ego-subgraph as Mermaid or DOT diagram

Returns:
  Query-specific results (caller/callee lists, hierarchy trees, paths, complexity metrics, diagrams, etc.)
```

---

### `graph_audit`

Full architectural audit: god nodes, security, dead code, complexity, communities, coupling, circular dependencies.

```
Parameters:
  repo_id (str)                 — Repository UUID from graph_build or repo_analyze
  audit_types (list[str]?)      — List of audit types to run (default: all)
  repo_path (str?)              — Optional path for graph-scoped queries
  include_summary (bool)        — Generate comprehensive markdown report (default: False)
  include_fix_suggestions (bool)— Attach graph_refactor call hints to god_node findings (default: False)
  degree_threshold (int)        — Min in-degree to classify as god node (default: 10)
  limit (int)                   — Max results per audit type (default: 50)
  fields (list[str]?)           — Return only these top-level result keys (e.g. ["god_nodes","security"]) — reduces token consumption

Audit Types (default all):
  "god_nodes"      → Symbols with high in-degree (central hubs); each entry includes fix_suggestion when include_fix_suggestions=True
  "security"       → Security hygiene issues
  "dead_code"      → Uncalled functions and unused code
  "complexity"     → Functions with highest cyclomatic complexity
  "communities"    → Leiden community clusters and coupling
  "circular_deps"  → Circular dependency chains
  "coupling"       → Surprising connections between unrelated modules

Returns:
  Findings organized by type with severity levels, optional markdown_summary, optional fix_suggestions
```

---

### `graph_build`

Build (or rebuild) the full code relationship graph for a repository using Tree-sitter parsing.

```
Parameters:
  repo_path (str)               — Absolute path to the repository root directory
  repo_id (str?)                — Optional UUID of the repository (auto-resolved if not provided)
  detect_modular (bool)         — Detect CODDY modular structure (default: True)
  build_dependency_graph (bool) — Build module dependency graph (default: True)
  include_core_contracts (bool) — Include core/Contracts/ as nodes in the graph (default: True)
  scan_hmvc_p (bool)            — Scan HMVC-P structure (default: True)
  max_depth (int)               — Maximum depth for submodule traversal (default: 5)
  use_cache (bool)              — Use cached graph if available (default: True)
  incremental (bool)            — Hash-based auto-invalidation: skip rebuild if files unchanged (default: True). Set False to force full rebuild.
  include_stats (bool)          — Whether to include node/edge count statistics (default: True)

Returns:
  Build result with modular summary, dependency graph, metrics, AI recommendations, graph_stats, and build_mode ("full_build" | "incremental_cache_hit" | "time_cache_hit")
```

---

### `graph_relationship`

Explore architecture relationships with community detection.

```
Parameters:
  repo_id (str)                — Repository UUID from graph_build or repo_analyze
  target_node (str)            — Target module/class/function name
  relation_type (list[str]?)   — "calls", "imports", "contains", "inherits"
  direction (str)              — "inbound" | "outbound" | "both" (default: "both")
  depth (int)                   — Exploration depth (default: 1)
  modular_type (str?)          — Filter by: "module" | "plugin" | "widget" | "component" | "service"
  include_community (bool)     — Include Leiden community detection results (default: False)
  min_confidence (str)         — Minimum confidence: "EXTRACTED" | "INFERRED" | "AMBIGUOUS" (default: "INFERRED")
  limit (int)                  — Maximum results (default: 100)
  cursor (str?)                — Pagination cursor

Returns:
  Relationship exploration with metrics and community info
```

---

### `graph_refactor`

Architectural-scale code transformation using graph-first approach.

```
Parameters:
  repo_id (str)              — Repository UUID from graph_build or repo_analyze
  action (str)               — "impact" | "preview" | "apply" | "undo" | "undo_list"
  refactor_type (str?)       — Required for impact/preview/apply; not needed for undo/undo_list
  target_node (str?)         — Required for impact/preview/apply
  options (dict?)            — Refactor-specific options (see Refactor Types below)
  dry_run (bool)             — If True, simulate only without writing changes (default: False)
  undo_id (str?)             — Undo log ID from a previous apply result; required for action="undo"

Actions:
  "impact"     → Analyze blast radius before refactoring
  "preview"    → Generate a diff preview without applying
  "apply"      → Apply the transformation; returns undo_id for reverting
  "undo"       → Retrieve and clear undo log entry by undo_id (provide undo_id)
  "undo_list"  → List up to 20 most recent undo log entries

Refactor Types:
  "split_module"         → Split a large module into domain-specific modules
  "extract_component"    → Extract a component with its dependencies (options: component_name, output_path)
  "reroute_dependency"   → Reroute a dependency to a different implementation (options: new_dependency)
  "extract_interface"    → Extract an interface from a concrete implementation (options: interface_name, interface_path)
  "inline_module"        → Inline a small module into its caller (options: caller_module)
  "extract_method"       → Extract a code block into a new method (options: method_name, start_line, end_line)
  "inline_function"      → Inline a trivial function into its callers (options: caller)

Returns:
  Impact analysis, preview, apply confirmation with undo_id, or undo log entries
```

---

## Tool Count

| Domain | Tool Count |
|--------|-----------|
| CodeGraph | 6 (graph_search, graph_query, graph_audit, graph_build, graph_relationship, graph_refactor) |

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| GRPH_001 | graph_build | Repository path does not exist or invalid |
| GRPH_002 | graph_query | Node not found in graph |
| GRPH_003 | graph_search | Invalid action parameter |
| GRPH_004 | graph_audit | Repository ID not found |
| GRPH_005 | graph_relationship | Target node not found |
| GRPH_006 | graph_refactor | Invalid refactor_type |
| GRPH_007 | graph_refactor | Target node not found in graph |
| GRPH_008 | graph_refactor | Undo log entry not found |
| GRPH_009 | graph_refactor | Apply operation failed |
| GRPH_010 | graph_build | Cache write/read error |
| GRPH_011 | graph_query | Invalid query_type parameter |
| GRPH_012 | graph_refactor | Validation failed (options, preconditions) |
