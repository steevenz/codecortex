# CodeCortex Unified Intelligence Engine: Final Concept

CodeCortex is a multi-dimensional intelligence engine designed to provide a unified "Source of Truth" for any codebase. It synthesizes physical, semantic, and relational data into a high-fidelity Knowledge Graph.

---

## 1. Project Architecture (Aegis DDD Standard)
CodeCortex is organized into four synergistic domains:

1. **Repository (Discovery)**: Manages physical file assets, classifications, and safety gatekeeping.
2. **CodeIndex (Semantics)**: Extracts symbol definitions and AST hierarchies using Tree-Sitter.
3. **CodeGraph (Connectivity)**: Maps logical relationships (Calls, Imports, Inheritance) between symbols.
4. **Graphify (Architectural Intelligence)**: Runs network algorithms to identify God Nodes, Surprising Connections, and Modularity Clusters.

---

## 2. The Master Source of Truth (Database Schema)
The `codecortex.db` merges all domains into a relational model that preserves both **Physical Hierarchy** and **Semantic AST Hierarchy**.

```mermaid
erDiagram
    repositories ||--o{ directories : organizes
    directories ||--o{ directories : nests
    directories ||--o{ files : contains
    files ||--o{ symbols : defines
    symbols ||--o{ symbols : nests
    symbols ||--o{ edges : sources
    symbols ||--o{ edges : targets
    repositories ||--o{ insights : characterizes
    repositories ||--o{ manifest_entries : tracks

    repositories {
        uuid id PK
        string name
        string root_path
        datetime last_indexed_at
    }
    directories {
        uuid id PK
        uuid repository_id FK
        uuid parent_id FK "Recursive"
        string relative_path
    }
    files {
        uuid id PK
        uuid directory_id FK
        string name
        enum classification "code|doc|config|binary"
        int size_bytes
        string content_hash
        datetime mtime
    }
    symbols {
        uuid id PK
        uuid file_id FK
        string parent_uid FK "AST Parent (Class/Module)"
        string code "Reference (file:type:name)"
        string name
        string symbol_type "class|func|method"
        int start_line
        int end_line
        string docstring
        string signature
    }
    edges {
        uuid id PK
        string source_code FK
        string target_code FK
        enum relation_type "CALLS|INHERITS|IMPORTS|USES"
        int line_number
        float weight
    }
    insights {
        uuid id PK
        uuid repository_id FK
        string target_code FK "Optional"
        string category "ARCH|SEC|QUAL"
        string insight_type "GOD_NODE|COUPLED_CLUSTER|SECRET_LEAK"
        json metadata
    }
    manifest_entries {
        uuid id PK
        uuid repository_id FK
        string file_path
        string last_hash
        datetime last_processed_at
    }
```

---

## 3. High-Resolution Intelligence Capabilities

### A. The Unified Codemap
Synthesis of Folder Structure + AST Symbol Nesting + Relationship Connectivity.
- **Value**: Visualizes not just *where* code is, but *what* it is and *who* it talks to.

### B. Execution Flow Tracking (Front Controller Trace)
Recursive traversal of the `CALLS` graph starting from a designated entry point.
- **Value**: Identifies the "Happy Path" and uncovers **Dead Code** (unreachable from the entry point).

### C. Modularity & Coupling Audits
Graph-based analysis of component density.
- **Cohesion**: Strength of internal relationships within a module.
- **Coupling**: External dependencies that create architectural "Spaghetti".
- **God Nodes**: Identifying overloaded components that act as centralized points of failure.

### D. Smart Ingestion & Hygiene
- **Secret Masking**: Proactive exclusion of `.env`, certificates, and sensitive patterns.
- **Office Conversion**: Automated Markdown sidecar generation for `.docx`/`.xlsx` documentation.
- **Incremental Indexing**: Manifest-based processing to only analyze changed files (Delta Analysis).

---

## 4. Analysis Pipeline (The "Cortex Lifecycle")

1. **Discovery Phase**: `Repository` scans files, applies `.gitignore`, and checks `manifest_entries` for deltas.
2. **Hygiene Phase**: `Graphify` masks secrets and prepares documentation sidecars.
3. **Semantic Phase**: `CodeIndex` performs Tree-Sitter parsing to build the `symbols` hierarchy.
4. **Relational Phase**: `CodeGraph` resolves cross-file references to populate the `edges` matrix.
5. **Analytical Phase**: `Graphify` runs graph algorithms to generate `insights`.
6. **Synthesis Phase**: `Orchestrator` package everything into the **Unified Context Envelope**.

---

## 5. Unified Response Envelope (Aegis API Standard)
Standardized output for high-fidelity intelligence retrieval:

```json
{
  "status": "success",
  "data": {
    "repository": { "project": "codecortex", "tree": {} },
    "intelligence": {
      "symbol_hierarchy": [],
      "connectivity_graph": { "nodes": [], "edges": [] }
    },
    "architectural_insights": {
      "god_nodes": [],
      "coupling_warnings": [],
      "security_hygiene": []
    }
  },
  "error": null,
  "metadata": {
    "version": "1.0.0",
    "timestamp": "ISO8601",
    "correlation_id": "uuid"
  }
}
```
