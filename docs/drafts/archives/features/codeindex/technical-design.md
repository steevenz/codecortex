# A.E.G.I.S <small>CODEWORK v0.1.0</small>
# CodeIndex: Technical Design

This document details the AST parsing pipeline and semantic storage strategy.

## 📐 Architecture

### Core Components

| Component | Responsibility |
|-----------|----------------|
| `CodeIndexService` | Orchestrates the parsing lifecycle and SQLite persistence. |
| `TreeSitterParser` | Bridge to C-based Tree-Sitter grammars. |
| `SymbolConverter` | DTO layer that normalizes AST nodes into the `RawSymbol` model. |
| `FrameworkDetector` | Injects framework-specific metadata into extracted symbols. |

## 🔄 Parsing Pipeline

```mermaid
graph TD
    A[File Content] --> B[Language Detection]
    B --> C{Grammar Available?}
    C -- Yes --> D[Tree-Sitter Parse]
    C -- No --> E[Fallback Parser]
    D --> F[Recursive Symbol Walk]
    E --> F
    F --> G[Extract Classes/Functions]
    G --> H[Extract Imports/Calls]
    H --> I[Nesting Resolution]
    I --> J[(SQLite symbols Table)]
```

### Symbol Nesting Resolution
The `CodeIndexService` implements a two-pass resolution strategy for parent-child relationships:
1. **Pass 1**: Extract all symbols and assign them unique UUIDs. Store their "Code Reference" (e.g., `Class.Method`).
2. **Pass 2**: Iterate through symbols and resolve `parent_id` by matching Code References against the UUID map created in Pass 1.

## 💾 Data Model: `symbols` Table

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier. |
| `repository_id` | UUID | Foreign key to `repositories`. |
| `parent_id` | UUID | Nullable; links to the parent symbol (e.g., Class). |
| `symbol_type` | Enum | `class`, `function`, `variable`, `interface`, etc. |
| `metadata` | JSON | Extended data: signatures, calls, docstrings. |
