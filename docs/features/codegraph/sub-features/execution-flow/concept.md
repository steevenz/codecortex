# Execution Flow

> **Source:** Integrated into `CodeGraphService` process detection

## Concept

Execution flow tracing reconstructs the **happy path** of a codebase — the sequence of function calls from an entry point (HTTP request, CLI command) through all downstream dependencies. This is done via BFS traversal of the call graph starting from a specific symbol.

## How It Works

```
graph_trace_flow("process_order", max_depth=5)
    │
    ▼
  process_order ──> validate_inventory ──> check_stock ──> query_db
         │                                       │
         └──> charge_payment ──> charge_gateway ──> http_post
         │
         └──> send_email ──> smtp_send
```

## BFS Traversal

1. Start node identified from `graph_find_symbols` or direct node ID
2. For each node, find all outgoing CALLS edges (immediate callees)
3. Recursively traverse callees up to `max_depth`
4. Deduplicate cycles (A calls B calls A) to prevent infinite loops
5. Return hierarchical tree with depth annotations

## Depth Configuration

| `max_depth` | Use Case | Typical Nodes |
|-------------|----------|--------------|
| 1-2 | Direct dependencies only | 5-20 |
| 3-5 | Full function trace | 20-100 |
| 5-10 | System-wide flow | 100-500 |


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
