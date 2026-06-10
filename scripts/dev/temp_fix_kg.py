import sys
# knowledge-graph/concept.md
path = 'docs/features/codegraph/sub-features/knowledge-graph/concept.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
if '## Error Codes' not in content:
    content += '''

---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| KG_001 | graph_build (knowledge_graph) | Dual-index invariant violated |
| KG_002 | graph_query (knowledge_graph) | Node lookup failed |

---

## Performance

- **Time Complexity:** All operations O(1) due to dual-index design
- **Memory Usage:** O(V+E) for storing graph data
- **Scalability:** Scales to ~100k nodes comfortably with O(1) lookups
- **Optimization:** Index updates are O(1) per insert
'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('OK knowledge-graph/concept.md')
