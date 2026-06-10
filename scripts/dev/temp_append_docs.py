import sys
files = [
    'docs/features/codegraph/sub-features/execution-flow/concept.md',
    'docs/features/codegraph/sub-features/architecture-audit/concept.md',
    'docs/features/codegraph/sub-features/graph-backends/concept.md',
    'docs/features/codegraph/sub-features/route-extraction/concept.md',
]

ef_template = '''

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| EF_001 | graph_query (execution_flow) | BFS traversal failed |
| EF_002 | graph_query (execution_flow) | Cycle detected (infinite loop prevention) |

---

## Performance

- **Time Complexity:** O(V+E) for BFS traversal
- **Depth Limiting:** Max depth parameter prevents runaway
- **Memory Usage:** O(depth) for recursion stack
- **Optimization:** Cycle detection prevents infinite loops
'''

aa_template = '''

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| AA_001 | graph_audit (architecture_audit) | Centrality calculation failed |
| AA_002 | graph_audit (architecture_audit) | Complexity calculation failed |

---

## Performance

- **Time Complexity:** O(V+E) for centrality, O(V) for complexity
- **Scalability:** Linear in graph size; fast for repos up to 100k nodes
- **Memory Usage:** O(V+E) for NetworkX graph in memory
- **Optimization:** Uses NetworkX built-in algorithms (highly optimized)
'''

gb_template = '''

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| GB_001 | graph_build (graph_backends) | Backend connection failed |
| GB_002 | graph_query (graph_backends) | Backend query failed |
| GB_003 | graph_build (graph_backends) | Backend schema migration failed |

---

## Performance

- **Latency:** Kuzu (embedded) ~5-10ms, Neo4j (client-server) ~20-50ms, FalkorDB (in-memory) ~1-5ms
- **Scalability:** Kuzu handles single-machine workloads, Neo4j scales horizontally, FalkorDB best for low-latency
- **Memory Usage:** Backend-specific; Neo4j requires more RAM than Kuzu
- **Optimization:** Fallback to SQLite if backend unavailable
'''

re_template = '''

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| RE_001 | graph_analyze (route_extraction) | Route pattern not recognized |
| RE_002 | graph_analyze (route_extraction) | Framework-specific extraction failed |

---

## Performance

- **Time Complexity:** O(N) for scanning route files
- **Regex Cost:** Pattern matching is linear in file size
- **Memory Usage:** O(R) for storing route metadata
- **Optimization:** Incremental scan based on file modification time
'''

templates = {
    'execution-flow': ef_template,
    'architecture-audit': aa_template,
    'graph-backends': gb_template,
    'route-extraction': re_template,
}

for f in files:
    with open(f, 'r', encoding='utf-8') as content:
        text = content.read()
    for sub in ['execution-flow', 'architecture-audit', 'graph-backends', 'route-extraction']:
        if sub in f:
            text += templates[sub]
            break
    with open(f, 'w', encoding='utf-8') as out:
        out.write(text)
    print(f'OK {f}')
