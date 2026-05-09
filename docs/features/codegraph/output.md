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
