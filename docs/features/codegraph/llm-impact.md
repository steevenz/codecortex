# CodeGraph: LLM Impact

## Before CodeGraph

An LLM with only symbol data can:
- Know what functions exist
- Know their signatures
- NOT know who calls them
- NOT know what they call
- NOT know the inheritance hierarchy
- NOT know the module dependency structure

## After CodeGraph

The LLM gains architectural awareness:

1. **Call Graph Awareness** — "What happens when I call `process_order`?" The LLM can see the complete transitive call chain: `process_order → validate_inventory → check_stock → query_database`.

2. **Impact Analysis** — "If I rename `UserService.authenticate`, what breaks?" The LLM can list every caller across the codebase.

3. **Architecture Understanding** — The LLM knows the module structure: which modules form a community, which are god modules, which have circular dependencies.

4. **Entry Point Discovery** — The LLM can identify HTTP routes, CLI commands, event handlers — the "front doors" to the system.

5. **Pattern Detection** — The LLM can identify design patterns by graph structure: observers (many callers of a single notification), strategies (multiple implementations of an interface), facades (single entry point to a complex subsystem).

## Concrete Improvements

| Capability | Without CodeGraph | With CodeGraph |
|-----------|------------------|----------------|
| Trace request flow | Manual file-by-file reading | BFS graph walk in milliseconds |
| Find dead code | Subjective guess | No incoming edges → confirmed dead |
| Assess refactor risk | Gut feeling | Exact call site list + count |
| Understand architecture | README (usually outdated) | Community detection from actual code |
| Detect god classes | None | Graph centrality metrics |
