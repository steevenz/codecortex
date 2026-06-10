# Relationships Action

**Purpose:** Show relationship graph between knowledge items and modules

## Why It Exists

Enables AI coders to understand how knowledge items relate to each other (decision→constraint, principle→decision) and to code modules, supporting impact analysis and architectural understanding.

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | Must be "relationships" |
| `focus` | string | ❌ | `null` | Topic to focus relationship subgraph on |
| `limit` | int | ❌ | `20` | Max edges (not currently implemented) |

## Output Format

```json
{
  "success": true,
  "status_code": 200,
  "message": "Knowledge graph: 89 relationships",
  "data": {
    "total": 89,
    "edges": [
      {
        "source": "a1b2c3d4e5f6",
        "source_meta": {
          "knowledge_type": "decision",
          "title": "Decision: Adopt CQRS for payment processing"
        },
        "target": "f6e5d4c3b2a1",
        "target_meta": {
          "knowledge_type": "constraint",
          "title": "Constraint: Write models are separate from read models"
        },
        "relation": "introduces",
        "weight": 0.7,
        "direction": "directed",
        "description": "Decision 'Adopt CQRS' introduces constraint",
        "created_at": "2026-05-29T10:30:00+00:00"
      }
    ],
    "statistics": {
      "density": 0.0234,
      "avg_degree": 3.45,
      "clustering": 0.1289,
      "unique_nodes": 47,
      "total_edges": 89
    },
    "focus": "CQRS"
  }
}
```

## Algorithm

**Without Focus:**
1. **Fetch All Chunks:** Retrieve top 200 chunks by importance_score
2. **Build Graph:** Build all relationships (type-based + tag-based)
3. **Return:** Return all edges

**With Focus:**
1. **Fetch All Chunks:** Retrieve top 200 chunks by importance_score
2. **Build Graph:** Build all relationships
3. **Find Focus Nodes:** Find chunks matching focus topic (title/content)
4. **Walk Graph:** Traverse graph from focus nodes (depth=2)
5. **Filter:** Return subgraph (nodes + edges) related to focus

## Relationship Types

| Type | Direction | Description | Example |
|------|-----------|-------------|---------|
| `introduces` | directed | Decision introduces constraint | Decision → Constraint |
| `refines` | directed | Principle refines decision | Principle → Decision |
| `violates` | directed | Anti-pattern violates principle | Anti-pattern → Principle |
| `affects` | directed | Risk affects module | Risk → Module |
| `references` | undirected | Chunks share tag | Chunk ↔ Chunk (same tag) |

## Graph Statistics

| Metric | Description |
|--------|-------------|
| `density` | Ratio of actual edges to possible edges (0-1) |
| `avg_degree` | Average connections per node |
| `clustering` | Transitivity coefficient (how connected are neighbors) |
| `unique_nodes` | Total unique entities in graph |
| `total_edges` | Total relationship edges |

## Use Case

**Scenario:** AI coder needs to understand impact of changing a constraint

**Workflow:**
1. Query relationships with focus on specific constraint
2. AI coder sees which decisions introduced the constraint
3. AI coder sees graph statistics (density shows how tightly coupled)
4. AI coder assesses impact of constraint change

## Error Cases

| Error Code | Description |
|------------|-------------|
| KG_500 | Internal error |
