# Project Structure Standard

> **Standard:** CODDY-ProjectStructure-v1.0
> **Applies to:** All domains in CodeCortex

## 1. Domain Directory Structure

Every domain MUST follow this structure:

```
src/modules/{domain}/
├── api/
│   ├── __init__.py
│   ├── tools.py          # MCP tool definitions (api_response compliant)
│   └── cli.py            # CLI command definitions
├── core/
│   ├── __init__.py
│   ├── extraction.py     # Knowledge extraction logic
│   ├── classification.py # Scoring + deduplication
│   └── graph.py          # Relationship building
├── adapters/
│   ├── __init__.py
│   ├── storage.py        # Persistence layer (SQLite + GoldenKnowledgeStore)
│   └── format_parser.py  # File format parsing (if needed)
├── models/
│   ├── __init__.py
│   ├── chunk.py          # KnowledgeChunk DTO
│   └── relationship.py   # DocRelationship DTO
└── __init__.py
```

## 2. api/tools.py Requirements

- MUST use `@mcp.tool()` decorator
- MUST call `api_response()` for all responses
- MUST use `new_request_id()` for request tracking
- MUST accept `orchestrator_factory` parameter in `register_tools()`
- MUST handle all errors with structured error codes
- MUST document all parameters in docstring with `@param` annotations
- MUST support `limit` parameter (capped at 200)

## 3. api/cli.py Requirements

- MUST define `DOMAIN` and `ALIASES` constants
- MUST use `output()`, `ok()`, `err()` helper functions
- MUST use `run_async()` for async coroutines
- MUST define `KG_COMMANDS` dict mapping action names to handler functions
- MUST define `build_parser(subparsers)` function
- MUST close orchestrator.db in `finally` blocks
- Error codes MUST follow `{DOMAIN}_{ descriptive name }` pattern

## 4. core/ Requirements

- MUST NOT import from `api/` layer (circular dependency prevention)
- MUST use DTOs from `models/` for all data transfer
- MUST be testable without MCP/CLI context
- Extraction logic MUST be pattern-based (no LLM dependency for core extraction)
- Scoring MUST use multi-dimension scoring with weights

## 5. adapters/ Requirements

- MUST wrap all 3rd-party dependencies
- MUST provide fallback when 3rd-party lib not installed
- Storage adapter MUST use dual-layer persistence (SQLite + GoldenKnowledgeStore)
- Format parser MUST normalize all formats to markdown-like text

## 6. models/ Requirements

- MUST use `@dataclass` for all DTOs
- MUST include `id` field (UUID, 12-char truncated)
- MUST include `to_dict()` method
- `to_dict()` MUST truncate large fields (content[:300], summary[:200])
- MUST include `created_at`, `updated_at` timestamps
- MUST include `repo_id` for multi-repo support

## 7. Compliance Checklist

- [ ] Directory structure matches standard
- [ ] `api/tools.py` uses `api_response()` and `new_request_id()`
- [ ] `api/cli.py` has `DOMAIN`, `ALIASES`, `KG_COMMANDS`, `build_parser`
- [ ] `core/` does not import from `api/`
- [ ] `adapters/` wraps 3rd-party deps
- [ ] `models/` uses dataclasses with `to_dict()` and truncation
- [ ] All files have `from __future__ import annotations`
