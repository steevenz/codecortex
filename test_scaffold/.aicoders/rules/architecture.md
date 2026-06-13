# Architecture Compliance Rules

> **Standard:** CODDY-Architecture-v1.0
> **Applies to:** All domains/modules in this project

## 1. Lego Principle (Modular Monolith)

- Each domain MUST be self-contained with clear boundaries
- Cross-domain dependencies MUST go through adapters/DTOs only
- No direct imports of internal module files from other domains
- Domain entry points: `api/tools.py` (MCP), `api/cli.py` (CLI)

## 2. Dependency Injection / IoC

- **Constructor injection ONLY** — no hardcoded `new Class()` or service locators
- All dependencies MUST be injected via `__init__` parameters
- Orchestrator factory pattern for MCP tools (avoids circular imports)

## 3. DTO Boundaries

- **Raw ORM models / HTTP requests MUST NOT leak across layers**
- Use DTOs (dataclasses) for ALL layer crossings
- DTOs MUST have `to_dict()` method for serialization
- DTO `to_dict()` MUST truncate large fields for token economy

## 4. Adapter Pattern

- All 3rd-party SDK interactions MUST be wrapped in local adapters
- Format parsing (docx, pdf, xlsx, pptx) → `adapters/format_parser.py`
- Storage (SQLite + GoldenKnowledgeStore) → `adapters/storage.py`
- No direct 3rd-party imports in core/domain logic

## 5. Codification

- Machine IDs: UUID (12-char truncated for display)
- Human codes: Readable business codes (e.g., KG_001, KG_EXTRACT_ERROR)
- Error codes MUST follow domain prefix pattern: `{DOMAIN}_{number}`

## 6. Clean Architecture Layers

```
api/        → MCP tools, CLI commands (input adapters)
core/       → Business logic, extraction, classification, graph
adapters/   → External service wrappers (storage, format_parser)
models/     → DTOs (chunk, relationship)
```

## 7. Compliance Checklist

- [ ] Constructor injection used everywhere
- [ ] DTOs used for all layer crossings
- [ ] No raw model leaks to API layer
- [ ] Adapters wrap all 3rd-party dependencies
- [ ] Error codes follow domain prefix standard
- [ ] `api_response()` used for all MCP tool responses
- [ ] `api/tools.py` and `api/cli.py` are the ONLY public APIs
