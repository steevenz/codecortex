# Query Action

**Purpose:** Query knowledge using natural language, regex, FTS5, glob, pattern, structured queries, vector similarity, or range filters.

## Why It Exists

Provides a unified, multi-mode search interface for engineering knowledge. AI coders can find relevant chunks using natural language, precise regex patterns, full-text search, wildcard globbing, structured query DSL, or vector embedding similarity — all in one API.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be "query" |
| `task` | string | ❌ | `null` | Natural language task description |
| `knowledge_types` | list | ❌ | `null` | Filter by knowledge type |
| `source_file` | string | ❌ | `null` | Filter by source file |
| `min_importance` | float | ❌ | `0.0` | Minimum importance score (0-1) |
| `max_importance` | float | ❌ | `null` | Maximum importance score (0-1) |
| `min_confidence` | float | ❌ | `0.0` | Minimum confidence score (0-1) |
| `max_confidence` | float | ❌ | `null` | Maximum confidence score (0-1) |
| `repo_id` | string | ❌ | `null` | Filter by repository ID |
| `semantic` | bool | ❌ | `false` | Enable semantic keyword overlap reranking |
| `fts_query` | string | ❌ | `null` | Full-text search query (SQLite FTS5, e.g. "payment AND constraint") |
| `regex` | string | ❌ | `null` | Regex pattern to match against content/title/summary |
| `glob` | string | ❌ | `null` | Glob pattern for source_file matching (e.g. "docs/**/*.md") |
| `pattern` | string | ❌ | `null` | Simple wildcard pattern (* and ?) against content |
| `structured_query` | dict | ❌ | `null` | Advanced structured query DSL (and/or/not per field) |
| `search_fields` | list | ❌ | `["title","content","summary"]` | Fields to apply regex/pattern to |
| `vector_search` | string | ❌ | `null` | Text for vector embedding cosine similarity |
| `limit` | int | ❌ | `20` | Max results (max 200) |

## Output Format

```json
{
  "success": true,
  "status_code": 200,
  "message": "Found 3 relevant knowledge items",
  "data": {
    "total": 3,
    "chunks": [
      {
        "id": "a1b2c3d4e5f6",
        "knowledge_type": "constraint",
        "type_label": "Constraint, rule, or invariant",
        "title": "Constraint: No direct DB access from Controllers",
        "content": "Controllers must not directly access the database...",
        "summary": "All data access through Service layer only.",
        "source_file": "docs/architecture/adr-001.md",
        "doc_type": "adr",
        "section_path": "## Constraints",
        "importance_score": 0.85,
        "criticality": "high",
        "concepts": ["Controller", "Service", "Repository"],
        "related_module": ["src/api/controllers", "src/domain/services"],
        "architecture_tag": ["architecture", "data"]
      }
    ],
    "types_available": {
      "concept": 12,
      "constraint": 8
    },
    "query": {
      "task": "payment service constraints",
      "types": ["constraint"],
      "min_importance": 0.7
    }
  }
}
```

## Search Modes

### 1. Full-Text Search (FTS5)
Uses SQLite FTS5 virtual table with Porter stemming and prefix matching.
```
fts_query: "payment AND constraint NOT deprecated"
```

### 2. Regex Search
SQLite REGEXP function matching against title/content/summary.
```
regex: "(?i)payment.*service"
```

### 3. Glob / Wildcard
SQLite GLOB for source_file paths; pattern for content wildcards.
```
glob: "docs/architecture/*.md"
pattern: "*payment*controller*"
```

### 4. Structured Query DSL
Dict-based AND/OR/NOT with per-field operators.
```json
{
  "and": [
    {"field": "knowledge_type", "op": "=", "value": "constraint"},
    {"field": "importance_score", "op": ">=", "value": 0.7},
    {"or": [
      {"field": "title", "op": "like", "value": "%payment%"},
      {"field": "content", "op": "regexp", "value": "(?i)auth"}
    ]}
  ]
}
```
Supported ops: `=`, `!=`, `<`, `>`, `<=`, `>=`, `like`, `not_like`, `in`, `not_in`, `glob`, `regexp`

### 5. Vector Embedding Search
Hash-based deterministic vectors (128-dim) with cosine similarity.
```
vector_search: "payment gateway architecture"
```

### 6. Range Queries
```
min_importance: 0.7, max_importance: 0.95
min_confidence: 0.6, max_confidence: 1.0
```

### 7. Task-Based Keyword / Semantic
```
task: "payment service database access constraints"
semantic: true  # enables keyword overlap similarity reranking
```

## Algorithm

1. **FTS5 Search:** If `fts_query` provided, use SQLite FTS5 (fastest, indexed)
2. **Regex Search:** If `regex` provided, match against search_fields via SQLite REGEXP
3. **Pattern Search:** If `pattern` provided, Python fnmatch.translate against content
4. **Structured Query:** If `structured_query` provided, compile DSL to SQL WHERE clause
5. **Standard Filtering:** Apply knowledge_types, source_file, repo_id, importance/confidence ranges, glob
6. **Vector Search:** If `vector_search` provided, compute cosine similarity against embeddings
7. **Task Reranking:** If `task` provided, keyword-match or semantic rerank results
8. **Relevance Score:** Compute per-chunk relevance_score based on final ranking position
9. **Limit & Explain:** Apply limit (capped at 200), build human-readable explanation

## Combining Search Modes

Modes can be combined for precise results:
```json
{
  "action": "query",
  "fts_query": "payment",
  "knowledge_types": ["constraint", "decision"],
  "min_importance": 0.7,
  "glob": "docs/architecture/*.md",
  "semantic": true,
  "limit": 10
}
```
Priority: FTS5 → Regex → Pattern → Structured Query → Standard Filters → Vector → Task/Semantic

## Use Case

**Scenario:** AI coder needs to understand constraints before implementing payment feature

**Workflow:**
1. Query with task: "payment service database access constraints"
2. AI coder receives relevant constraints with importance scores
3. AI coder applies constraints during implementation

## Error Cases

| Error Code | Description |
|------------|-------------|
| KG_003 | At least one search parameter required (task, fts_query, regex, glob, pattern, structured_query, or vector_search) |
| KG_500 | Internal error |
