# Graph Backends

> **Source:** `src/core/graph_manager.py`

## Concept

CodeGraph supports multiple graph database backends for persisting and querying the code relationship graph. This enables different scalability and performance profiles.

## Supported Backends

| Backend | Type | Setup | Query Language | Best For |
|---------|------|-------|---------------|----------|
| **Kuzu** | Embedded columnar | Auto (pip package) | Cypher subset | Single-machine, fast local queries |
| **Neo4j** | Client-server | Docker | Cypher | Team-scale, existing Neo4j infra |
| **FalkorDB** | In-memory Redis | Docker | RedisGraph | Low-latency, real-time queries |
| **SQLite** (fallback) | Relational | Built-in | SQL | Zero-setup, embedded |

## Backend Selection

The backend is selected via `CODECORTEX_GRAPH_BACKEND` env var:

```
CODECORTEX_GRAPH_BACKEND=kuzu      # Default if kuzu is installed
CODECORTEX_GRAPH_BACKEND=neo4j     # Requires running Neo4j instance
CODECORTEX_GRAPH_BACKEND=falkordb  # Requires running FalkorDB instance
```

If the env var is unset and `kuzu` is installed, Kuzu is used. Otherwise, SQLite is the fallback.

## Graph Schema (Cypher)

```cypher
(:Repository {id, name, path})
  -[:CONTAINS]->(:File {path, language})
    -[:DEFINES]->(:Function {name, line, signature, async})
    -[:DEFINES]->(:Class {name, line, bases})
  (:Function)-[:CALLS {line}]->(:Function)
  (:Class)-[:INHERITS]->(:Class)
  (:File)-[:IMPORTS]->(:File)
```

## Docker Setup

```bash
docker-compose up -d     # Starts Neo4j + FalkorDB
```
