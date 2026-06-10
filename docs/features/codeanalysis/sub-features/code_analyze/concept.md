# Code Analyze Tool

**Tool:** `code_analyze`  
**Category:** Code Analysis  
**Domain:** CodeAnalysis  
**Version:** 2.0.0  
**AI Coder Impact:** 10/10 ⭐

---

## Overview

The `code_analyze` tool provides deep semantic code analysis with AST (Abstract Syntax Tree) awareness using Tree-Sitter. It extracts symbols, builds call graphs, and provides multi-mode analysis including batch processing and parallel execution.

## Capabilities

### Analysis Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `auto` | Automatic mode selection | General purpose analysis |
| `overview` | Directory tree structure | Quick project overview |
| `detailed` | Symbol extraction with details | Deep code understanding |
| `symbol_focus` | Focus on specific symbol | Trace call chains |
| `batch_detailed` | Multi-target parallel analysis | Analyze multiple files/directories |

### Key Features

- **Batch Analysis** — Process multiple targets in parallel with configurable workers
- **Call Graph Traversal** — Trace function calls with configurable depth
- **AST-Aware** — Tree-Sitter based parsing for accurate symbol extraction
- **Symbol Details** — Extract signatures, docstrings, and relationships
- **Cross-Target Graphs** — Build call graphs across multiple files

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | Yes | - | File or directory path to analyze |
| `targets` | list[string] | No | - | List of multiple targets for batch analysis |
| `mode` | string | No | "auto" | Analysis mode: auto, overview, detailed, symbol_focus, batch_detailed |
| `max_depth` | int | No | 3 | Max traversal depth for overview mode (max 10) |
| `focus` | string | No | - | Symbol name for symbol_focus mode |
| `follow_depth` | int | No | 1 | Call graph traversal depth (max 3) |
| `cursor` | string | No | - | Pagination cursor for large results |
| `page_size` | int | No | 100 | Items per page (max 500) |
| `include_docstring` | bool | No | true | Include docstrings in results |
| `include_comments` | bool | No | false | Include comments in results |
| `repo_id` | string | No | - | Repository UUID for scope |
| `parallel` | bool | No | true | Enable parallel processing for batch analysis |
| `max_workers` | int | No | 4 | Thread pool size for parallel processing |

## Output

### Result Structure

```json
{
  "mode": "detailed",
  "target": "/path/to/code",
  "count": 42,
  "symbols": [
    {
      "name": "PaymentProcessor",
      "kind": "class",
      "file": "src/payment/processor.py",
      "line_start": 15,
      "line_end": 120,
      "signature": "class PaymentProcessor(ABC):",
      "docstring": "Processes payment transactions with validation",
      "parent_symbol": null,
      "calls": ["validate", "execute", "log"],
      "referenced_by": ["PaymentService", "TransactionController"]
    }
  ],
  "edges": [
    {
      "from_symbol": "PaymentProcessor",
      "to_symbol": "validate",
      "relation": "calls",
      "weight": 1.0
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

## Batch Analysis

### Parallel Processing

When analyzing multiple targets, the tool uses a thread pool for parallel execution:

```python
request = AnalyzeRequest(
    target="src/",  # Fallback target
    targets=["src/module1/", "src/module2/", "src/module3/"],
    mode="batch_detailed",
    parallel=True,
    max_workers=4,
)
```

### Cross-Target Call Graphs

Batch analysis builds call graphs across all analyzed targets, showing inter-module dependencies.

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| CA_001 | high | Target path does not exist |
| CA_002 | high | Symbol not found (symbol_focus mode) |
| CA_500 | critical | Internal error |

## Examples

### Basic Analysis

```python
# Analyze directory structure
result = code_analyze(target="src/", mode="overview")

# Deep analysis of a file
result = code_analyze(target="src/payment/processor.py", mode="detailed")
```

### Symbol Focus

```python
# Trace call chain for a specific symbol
result = code_analyze(
    target="src/",
    mode="symbol_focus",
    focus="PaymentProcessor",
    follow_depth=2,
)
```

### Batch Analysis

```python
# Analyze multiple modules in parallel
result = code_analyze(
    target="src/",
    targets=["src/auth/", "src/payment/", "src/user/"],
    mode="batch_detailed",
    parallel=True,
    max_workers=4,
)
```

## Performance

- **Parallel Processing** — Configurable thread pool for batch operations
- **AST Caching** — Reuse parsed AST for performance
- **Pagination** — Cursor-based pagination for large codebases

## Dependencies

- **Tree-Sitter** — AST parsing (optional, falls back to regex)
- **Database** — Symbol and relationship storage
- **Filesystem Service** — File discovery and reading

## See Also

- [Search Tool](../sub-features/code_search/concept.md)
- [Audit Tool](../sub-features/code_audit/concept.md)
- [Status Tool](../sub-features/code_status/concept.md)
