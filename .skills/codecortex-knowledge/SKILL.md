---
name: codecortex-knowledge
description: Use when extracting engineering knowledge from documentation, querying architectural decisions/constraints/risks/principles, validating code against documented rules, or building institutional memory from brownfield codebases via CodeCortex
---

# codecortex:knowledge — Engineering Knowledge Graph (WFK_LGY_001)

**5 actions**: `extract | query | status | relationships | validate`

**Tool**: `codecortex:knowledge`

**Docs**: `docs/features/knowledgegraph/concept.md` | `docs/workflows/brownfield-workflow.md` (WFK_LGY_001)

---

## What It Extracts

8 knowledge types from `.md, .rst, .txt, .adoc, .csv, .json, .log, .docx, .pdf, .xlsx, .pptx`:

| Type | What | Example |
|------|------|---------|
| `architectural_decision` | ADR entries | "Use PostgreSQL for persistence" |
| `constraint` | Technical limits | "No direct DB from controllers" |
| `risk` | Known issues | "Rate limiting not implemented" |
| `principle` | Design philosophy | "Favor composition over inheritance" |
| `flow` | Process description | "Payment: validate → auth → charge → notify" |
| `api_contract` | Endpoint specs | "POST /api/orders → {items, total}" |
| `invariant` | Always-true rules | "User.email must be unique" |
| `reference` | External links | "See https://docs.example.com/auth" |

**Scoring**: Importance 0-1, Confidence 0-1. High-importance items auto-tagged as `GoldenKnowledge`.

---

## action: extract — Scan & Extract Knowledge

```
action: extract
args: {repo_path:, knowledge_types?, repo_id?}
```

Incremental: SHA-256 hash skips unchanged files (uses `extraction_log`).

Returns `{documents_scanned, chunks_extracted, relationships_built, by_type, avg_confidence}`.

**Token economy**: 5 scored knowledge chunks vs 50 pages of raw docs = ~90% reduction.

---

## action: query — Structured Retrieval

```
action: query
args: {task?, knowledge_types?, source_file?, repo_id?,
       semantic:?, fts_query:?, regex:?, glob:?, pattern:?,
       vector_search:?, structured_query:?,
       min_importance:0, max_importance:?, limit:20}
```

**Search strategies:**
| Method | When | Example |
|--------|------|---------|
| `task` | Natural language | `"How to implement payment?"` |
| `fts_query` | Exact match | `"payment AND constraint"` (SQLite FTS5) |
| `regex` | Pattern | `"postgres|mysql"` |
| `semantic:true` | Conceptual | Cosine similarity on embeddings |
| `vector_search` | Similar content | Embedding comparison |
| `structured_query` | Complex filter | `{and: [{type: "constraint"}, {repo_id: "x"}]}` |

**Returns**: `{items[{title, content, type, importance, confidence, source_file}], total}`

---

## action: status — Extraction Coverage

```
action: status
args: {repo_id?}
```

Returns `{documents, chunks, by_type, avg_confidence_score, sources[]}`.

---

## action: relationships — Knowledge Graph

```
action: relationships
args: {focus?, limit:20}
```

Links decisions → constraints → modules → code files. Shows how knowledge connects.

---

## action: validate — Code vs Constraints (WFK_LGY_003)

```
action: validate
args: {repo_path:}
```

Validates actual code against extracted constraints. Finds violations.

---

## Brownfield Integration (WFK_LGY_001)

From `docs/workflows/brownfield-workflow.md`:

**Phase 4 — Knowledge Extraction from Documentation:**
```
repo init + analyze          → build AST index + graph
knowledge extract repo_path  → extract 8 types
knowledge query task:"arch"  → verify extraction quality
knowledge relationships      → build knowledge graph
```

After extraction, future AI agents query knowledge before modifying code:
```
knowledge query task: "I want to add a payment method"
```
If constraints found → acceptance criteria. If nothing → document decisions after.

---

## Integration Pattern

```
1. repo init + analyze           → index repo
2. knowledge extract repo_path:  → build knowledge base
3. knowledge query task:"auth"   → get constraints
4. cb search query:"auth"        → find implementation
5. knowledge validate repo_path: → check compliance
```

---

## Rule of Thumb

**Before** any code modification on brownfield projects, query knowledge first. If relevant constraints exist, they become your acceptance criteria. If no constraints exist, document the new design decisions after implementation so the next agent benefits.

---

## Feature Docs

| Resource | Path |
|----------|------|
| Concept | `docs/features/knowledgegraph/concept.md` |
| AI-Impact | `docs/features/knowledgegraph/ai-impact-token-efficiency.md` |
| Examples | `docs/features/knowledgegraph/examples/adr-extraction.md` |
| Brownfield Workflow | `docs/workflows/brownfield-workflow.md` (WFK_LGY_001) |
| IDE Context Workflow | `docs/workflows/ide-context-workflow.md` (WFK_IDE_001) |
