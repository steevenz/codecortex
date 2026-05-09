# Community Detection

> **Source:** Integrated into `CodeGraphService`

## Concept

Community detection groups related code modules into clusters ("communities") based on their dependency patterns. This reveals the **de facto architecture** — how code actually groups together — which may differ from the intended folder structure.

## Algorithm: Leiden

Leiden is the primary algorithm with Louvain as automatic fallback.

| Property | Leiden | Louvain |
|----------|--------|---------|
| Speed | Faster | Slower for large graphs |
| Quality | Higher modularity | Good modularity |
| Resolution | Guaranteed connected communities | Can produce disconnected communities |
| Complexity | O(V log V) | O(V log V) |

## Output

```json
{
  "num_communities": 5,
  "modularity": 0.73,
  "algorithm": "leiden",
  "communities": [
    {
      "id": 0,
      "size": 15,
      "cohesion": 0.89,
      "members": [
        {"name": "UserService", "file": "src/domain/user/service.py"},
        {"name": "AuthMiddleware", "file": "src/api/middleware/auth.py"},
        {"name": "UserRepository", "file": "src/infrastructure/repositories/user.py"}
      ]
    }
  ]
}
```

## Interpretation

- **High cohesion (>0.8):** The community represents a well-encapsulated module
- **Low cohesion (<0.5):** The community may need restructuring
- **Small communities (2-5):** Likely utility groups
- **Large communities (20+):** May indicate a god module
