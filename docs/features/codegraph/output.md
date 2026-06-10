# CodeGraph: Output Data

## Response Shapes

### `graph_query` — Callers Example

```json
{
  "query_type": "callers",
  "target": "process_payment",
  "results": [
    {
      "symbol_name": "checkout_cart",
      "symbol_type": "function",
      "file": "src/api/checkout.py",
      "line": 42,
      "language": "python"
    },
    {
      "symbol_name": "retry_failed_payment",
      "symbol_type": "function",
      "file": "src/domain/payments/retry.py",
      "line": 15,
      "language": "python"
    }
  ],
  "total": 2
}
```

### `arch_analyze` — Community Structure

```json
{
  "communities": [
    {
      "id": 0,
      "size": 12,
      "members": ["UserService", "AuthHandler", "UserModel", "TokenProvider"],
      "cohesion": 0.87
    },
    {
      "id": 1,
      "size": 8,
      "members": ["PaymentGateway", "InvoiceService", "BillingModel"],
      "cohesion": 0.92
    }
  ],
  "modularity": 0.73,
  "algorithm": "leiden"
}
```

### `arch_audit` — God Nodes

```json
{
  "god_nodes": [
    {
      "name": "Utils",
      "type": "module",
      "file": "src/utils/__init__.py",
      "in_degree": 47,
      "out_degree": 32,
      "risk": "high",
      "recommendation": "Split into domain-specific utility modules"
    }
  ]
}
```

## Graph Backend Storage

When Kuzu/Neo4j/FalkorDB is configured, graph data is also stored as:

| Graph Entity | Node Label | Key Properties |
|-------------|-----------|---------------|
| Repository | `Repository` | id, name, path |
| File | `File` | path, language |
| Function | `Function` | name, line, signature |
| Class | `Class` | name, line, bases |
| Relationship | Edge type | CALLS, INHERITS, IMPORTS, USES, DEFINES |

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

---

## Performance

- **Response Size:** Graph backend queries return paginated results to limit token consumption
- **Caching:** In-memory KnowledgeGraph with dual-index for O(1) lookups; avoids repeated database hits
- **Backend Sync:** Optional Kuzu/Neo4j/FalkorDB sync for persistent graph queries; adds ~50ms overhead per query
- **Visualization:** DOT/Mermaid diagram generation is O(V+E) and bounded by max_depth parameter
