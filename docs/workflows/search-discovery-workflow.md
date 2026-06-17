---
description: Advanced Search & Discovery — text, semantic, graph-enriched, and symbol-focused code search
title: WFK_SCH_001 — Advanced Search & Discovery
workflow_id: WFK_SCH_001
version: 1.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
---

# WFK_SCH_001: Advanced Search & Discovery

> **Goal**: Find code, symbols, and relationships using the optimal search strategy for each query type.
> **Trigger**: User asks to find code, search symbols, trace calls, or discover dead code.
> **Time**: <1s (text) to 5s (graph-enriched).
> **Cost**: Low (FTS5) to Medium (semantic + graph).
> **Codification**: CODDY-Architecture-v1.0 §5 — `WFK_SCH_001`

---

## 1. Trigger Phrases

- *"Find symbol / Where is X defined?"*
- *"Search code"*
- *"Semantic search"*
- *"Who calls this function?"*
- *"Trace call chain"*
- *"Find dead code"*
- *"Lookup class / module"*
- *"Conceptually related code"*
- *"Graph-enriched search"*
- *"Search with relationships"*

---

## 2. Search Strategy Decision Tree

```
User Query
│
├──► Exact keyword / String literal search
│      └──► Text Search (FTS5)
│
├──► Concept / Idea search (fuzzy match)
│      └──► Semantic Search (embeddings)
│
├──► Symbol with relationships (callers, callees, inherits)
│      └──► Graph-Enriched Search
│
├──► Deep symbol details (signature, docstring, calls)
│      └──► Symbol-Focus Analysis
│
└──► Unused / Unreferenced code
       └──► Dead Code Discovery
```

---

## 3. Mode 1 — Text Search (FTS5)

**When**: Exact keyword, string literal, error message fragment, function name.

### MCP Call
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "process_order",
    search_type: "text",
    file_pattern: "*.py",
    include_content: true,
    limit: 20
  }
```

### AI Must Read
| Field | Usage |
|-------|-------|
| `matches[].score` | FTS5 relevance (0-1). Higher = better text match. |
| `matches[].file` | File location. |
| `matches[].line` | Exact line number. |
| `matches[].content` | Surrounding context (use for quoting). |

### CLI
```bash
codecortex cb search "process_order" --repo-id <uuid> --file-pattern "*.py"
```

---

## 4. Mode 2 — Semantic Search

**When**: User describes a concept, not a literal string. Finds conceptually related code even with different naming.

### MCP Call
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "authentication token handling and refresh logic",
    search_type: "text",
    semantic: true,
    limit: 20
  }
```

### AI Must Read
| Field | Usage |
|-------|-------|
| `semantic_hits[].similarity` | Cosine similarity (0-1). Higher = conceptually closer. |
| `semantic_hits[].file` | Source file. |
| `semantic_hits[].symbol` | Matching symbol name. |

### When Text Search Fails, Try Semantic
If `cb:search` text mode returns 0 results:
1. Re-run with `semantic: true`
2. Use broader, more conceptual query
3. Add `graph_enrichment: true` for relationship context

---

## 5. Mode 3 — Graph-Enriched Search

**When**: Need to understand how a symbol relates to others — callers, callees, inheritance.

### MCP Call
```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "UserService",
    search_type: "text",
    semantic: false,
    graph_enrichment: true,
    graph_relations: ["CALLS", "INHERITS", "IMPORTS"],
    limit: 20
  }
```

### Direct Graph Queries (Alternative)
```
# Find callers
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "src/services/user.py::UserService",
    query_type: "callers",
    max_depth: 3,
    direction: "upstream"
  }

# Find callees
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "src/services/user.py::UserService",
    query_type: "callees",
    max_depth: 3,
    direction: "downstream"
  }
```

---

## 6. Mode 4 — Symbol-Focus Analysis

**When**: Deep dive into a specific class/function — signature, docstring, call graph.

### MCP Call
```
MCP: codecortex:codebase
  action: "analyze"
  repo_id: "<repo_id>"
  args: {
    target: "src/services/user.py::UserService",
    mode: "symbol_focus",
    max_depth: 5,
    follow_depth: 2,
    include_docstring: true,
    include_comments: true
  }
```

---

## 7. Mode 5 — Dead Code Discovery

**When**: Finding unused functions, classes, or variables for cleanup.

### MCP Call
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "query",
    target: "*",
    query_type: "dead_code",
    limit: 50
  }
```

### CLI
```bash
codecortex cg query dead_code --repo-id <uuid> --limit 50
```

---

## 8. Multi-Criteria Combined Search

**When**: Need to combine text + semantic + graph in one query.

```
MCP: codecortex:codebase
  action: "search"
  repo_id: "<repo_id>"
  args: {
    query: "payment gateway integration",
    search_type: "text",
    semantic: true,
    graph_enrichment: true,
    graph_relations: ["CALLS", "IMPORTS"],
    file_pattern: "*.py",
    limit: 20
  }
```

**AI reads**: Both `matches[]` (text) and `semantic_hits[]` (conceptual) and `relationships[]` (graph).

---

## 9. Deliverable Format

```markdown
# Search Report: "<query>"

## 1. Results Summary
- **Mode**: <text/semantic/graph/dead_code>
- **Total Matches**: <N>
- **Top Match Score**: <N>

## 2. Key Findings
| Symbol | File | Line | Score | Relation |
|--------|------|------|-------|----------|
| ... | ... | ... | ... | ... |

## 3. Relationship Map (if graph-enriched)
```
<CallerA>
  → <CallerB>
    → <TargetSymbol>  <-- MATCH
      → <CalleeC>
```

## 4. Recommendations
- <next search to run>
- <symbols to investigate>
```

---

## 10. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| Always start with `search_type: "text"` | ~25% | FTS5 is cheapest |
| `include_content: false` for initial scan | ~40% | Only get file paths |
| `limit: 10` for text search | ~50% | Narrow before broadening |
| Skip `graph_enrichment` if text search already found exact symbol | ~20% | No need for relationships |

### Parallel Execution
- Mode 1 (text) + Mode 2 (semantic) can run in parallel for the same query
- Mode 3 (graph-enriched) depends on Mode 1/2 results → sequential
- Mode 4 (symbol-focus) + Mode 5 (dead code) are independent → parallel

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| Text search returns exact match with line number | Deliver immediately, skip semantic/graph |
| User asks "where is X defined?" | Use `cb:analyze symbol_focus` directly, skip search |
| `matches[].score >= 0.95` | Exact match found → skip other modes |
| Semantic search returns 0 results | Switch to graph query with broader target |

### Cache Reuse
- If `cb:search` ran in last 5 minutes with same query → reuse
- Graph query results valid until `repo:sync` detects changes
- Semantic embeddings cached per `repo_id` — no re-computation needed

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [deep-analysis-workflow.md](deep-analysis-workflow.md) | [UnifiedSearch](../features/unified-search/concept.md)*
