# A.E.G.I.S <small>CODEWORK v0.1.0</small>
# CodeGraph: Technical Design

This document details the relationship resolution logic and graph persistence architecture.

## 📐 Architecture

### Core Components

| Component | Responsibility |
|-----------|----------------|
| `CodeGraphService` | Orchestrates the relationship resolution and backend sync. |
| `GraphManager` | Abstracted interface for graph backend operations. |
| `CallResolver` | Logic for matching call sites to symbol definitions. |
| `GraphWriter` | Batch persistence layer for nodes and edges. |

## 🔄 Relationship Resolution Logic

### 1. Global Pre-scan (Python Example)
To resolve calls efficiently, CodeGraph performs a global pre-scan of imports:
- **Map Generation**: Creates a dictionary mapping `SymbolName -> FilePath`.
- **Ambiguity Resolution**: Uses import statements within each file to narrow down the possible target for a given name.

### 2. Edge Creation Flow
- **Step 1**: Fetch all symbols from the `symbols` table.
- **Step 2**: Process `metadata.function_calls` for each symbol.
- **Step 3**: Attempt to match the callee name against the global map.
- **Step 4**: Create a `CALLS` edge if a match is found.

## 💾 Graph Schema (Kùzu / Neo4j)

### Nodes
- `(:File {path, name, is_dependency})`
- `(:Function {uid, name, signature, line_number})`
- `(:Class {uid, name, line_number})`

### Edges
- `(:File)-[:CONTAINS]->(:Function|:Class)`
- `(:Function|:Class)-[:CALLS]->(:Function|:Class)`
- `(:Class)-[:INHERITS]->(:Class)`

## 🚀 Batch Synchronization

CodeGraph uses a "Bulk Load" strategy for persistence:
- **Merge Logic**: Nodes are merged based on their stable `uid` (e.g., `fn:{path}:{name}:{line}`).
- **Batching**: Calls and inheritance edges are collected into memory and written in large chunks to minimize network/disk round-trips.
