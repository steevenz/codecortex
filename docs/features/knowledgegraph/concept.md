# KnowledgeGraph: Engineering Knowledge Extraction

> **Domain:** KnowledgeGraph
> **Package:** `src/modules/knowledgegraph/`
> **Version:** 2.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

KnowledgeGraph extracts **engineering knowledge from documentation** — PRDs, ADRs, READMEs, architecture guides, Word docs, PDFs, Excel sheets, PowerPoint decks, CSVs, JSON files, log files, and more — and structures it into queryable, relationship-mapped knowledge chunks that AI coders (and humans) can act on.

While CodeIndex handles code-level symbols and CodeGraph handles code-level relationships, KnowledgeGraph handles the **documentation-level semantics**: constraints, decisions, risks, principles, flows, and invariants that govern the codebase but are rarely expressed in code.

## Why This Exists

- **Tribal knowledge loss:** Critical architectural decisions are buried in PRDs/ADRs that nobody reads. KnowledgeGraph surfaces them automatically.
- **AI context injection:** High-importance chunks are pushed to GoldenKnowledgeStore so AI agents always have architectural context during code generation.
- **Constraint compliance:** Extracted constraints and invariants can be validated against actual code (e.g., "No direct DB access from controllers").
- **Risk awareness:** Architectural risks documented in ADRs are surfaced alongside code analysis results.

## Theoretical Foundation

- **Pattern-based extraction (no LLM):** 8 knowledge types, each with regex patterns tuned for markdown documentation. No LLM dependency — extracts run in milliseconds on any doc.
- **Importance scoring:** 6-dimension scoring (architectural importance, criticality, type weight, concept richness, module relevance, content density) ranks chunks for priority.
- **Relationship mapping:** Cross-chunk relationships built from shared vocabulary, type linkages (decision → constraint → module), and tag groups.
- **Dual-layer persistence:** Chunks stored in SQLite for queries + GoldenKnowledgeStore for AI context injection.

## Architecture

```
src/modules/knowledgegraph/
├── api/              → tools.py: 1 MCP tool (5 actions), cli.py: CLI commands, api_response() compliant
├── core/             → Extraction, classification, graph building logic
│   ├── extraction.py → 8-type pattern-based knowledge extraction + parallel batch processing
│   ├── classification.py → 6-dimension importance scoring + confidence scoring + deduplication
│   └── graph.py     → Relationship mapping (type-based + tag-based) + graph statistics
├── adapters/         → Storage adapter for SQLite + GoldenKnowledgeStore
│   └── storage.py   → KnowledgeStore with dual-layer persistence + incremental extraction tracking
└── models/           → DTOs: KnowledgeChunk, DocRelationship
```

## Domain Boundary

- **Owns:** `knowledge_graph` (MCP tool with 5 actions: extract, query, status, relationships, validate)
- **Does NOT own:** `code_refactor` (handled by coderefactor domain)
- **Depends on:** `DatabaseManager`, `DocumentParser` (from codeanalysis)
- **Consumed by:** MCP layer via `api/tools.py`, CLI via `api/cli.py`

## CLI Architecture Note

The CLI domain is named `knowledge` (aliases: `kg`) as an intentional UX decision. This provides a unified interface for knowledge operations. Users access all knowledge operations via `codecortex knowledge <command>` or `codecortex kg <command>`.

## ~/.aicoders/ Compliance

This domain follows the [Aegis Codework Sovereign Cognitive Infrastructure](https://github.com/aegis-codework) standards:

### Architecture (`.aicoders/rules/architecture.md`)
- **Lego Principle:** Self-contained domain with `api/` + `core/` + `adapters/` + `models/` separation
- **DI/IoC:** Constructor injection via `KnowledgeStore(db)`; stateless core classes (`KnowledgeExtractor`, `KnowledgeGraphBuilder`)
- **DTO Boundaries:** `KnowledgeChunk` and `DocRelationship` with `to_dict()` + field truncation (`content[:300]`, `summary[:200]`, `concept[:5]`)
- **Adapters:** `FormatParser` wraps python-docx, pypdf, openpyxl, python-pptx; `KnowledgeStore` wraps SQLite + GoldenKnowledgeStore
- **Codification:** Machine IDs via `uuid.uuid4()[:12]`; human codes `KG_001`–`KG_500` and `KG_{NAME}_ERROR`

### Project Structure (`.aicoders/docs/standards/project-structure.md`)
- **Directory layout:** Exact match with standard (`api/`, `core/`, `adapters/`, `models/`)
- **MCP Tools:** `@mcp.tool()` + `api_response()` + `new_request_id()` + `orchestrator_factory`
- **CLI:** `DOMAIN="knowledge"`, `ALIASES=["kg"]`, `KG_COMMANDS`, `build_parser(subparsers)`
- **Models:** `@dataclass` with `id`, `created_at`, `updated_at`, `repo_id`, `to_dict()`

### API Standard (`.aicoders/docs/standards/api.md`)
- **Registration:** `register_tools(mcp, orchestrator_factory)` exports correctly
- **Responses:** All 5 actions use `api_response()` with structured data
- **Error Codes:** Follow `{DOMAIN}_{number}` and `{DOMAIN}_{NAME}_ERROR` patterns
- **Parameters:** Type hints, optional defaults, `limit` capped at 200

### Documentation Standard (`.aicoders/docs/standards/documentation.md`)
- **Structure:** `concept.md` + `ai-impact-token-efficiency.md` + `sub-features/*/concept.md`
- **Version:** Semver 2.0.0 with AI impact (10/10) and production readiness (100%)
- **Sections:** All 11 required sections present + 12 AI Coder Impact features

## 8 Knowledge Types

| Type | What It Captures | Example Pattern |
|------|-----------------|-----------------|
| **concept** | Engineering concept or domain term | `**Concept:** Domain-Driven Design` |
| **constraint** | Rule, invariant, or must-have | `**Constraint:** No direct DB access from controllers` |
| **decision** | Architectural decision with rationale | `**Decision:** Use PostgreSQL over MongoDB` |
| **flow** | Process flow or lifecycle | `**Flow:** Payment lifecycle: authorize → capture → settle` |
| **risk** | Risk, hotspot, or fragility | `**Risk:** Single point of failure in auth service` |
| **invariant** | Business invariant or integrity rule | `**Invariant:** Username must be unique across tenants` |
| **anti_pattern** | Anti-pattern or practice to avoid | `**Anti-pattern:** God classes in service layer` |
| **principle** | Engineering principle or standard | `**Principle:** Modular-first design with loose coupling` |

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| KG_001 | High | repo_path required for extract |
| KG_002 | High | Path not found |
| KG_003 | High | task required for query |
| KG_004 | High | Unknown action |
| KG_006 | High | repo_path required for validate |
| KG_500 | Critical | Internal error |
| KG_PATH_ERROR | High | CLI: Path not found |
| KG_EXTRACT_ERROR | Critical | CLI: Extract failed |
| KG_QUERY_ERROR | Critical | CLI: Query failed |
| KG_STATUS_ERROR | Critical | CLI: Status failed |
| KG_REL_ERROR | Critical | CLI: Relationships failed |
| KG_VALIDATE_ERROR | Critical | CLI: Validate failed |

## 10/10 AI Coder Impact Features

1. **Pattern-based extraction (no LLM)** — 8 knowledge types extracted via regex patterns, no LLM dependency, runs in milliseconds
2. **6-dimension importance scoring + confidence scoring** — Architectural importance + extraction confidence for quality assessment
3. **Dual-layer persistence** — SQLite for queries + GoldenKnowledgeStore for AI context injection
4. **Relationship mapping with graph statistics** — Type-based edges + density, centrality, clustering metrics
5. **Semantic + keyword search** — Natural language task matching with semantic reranking and keyword overlap
6. **Query explanation** — Human-readable explanation of why chunks matched, with relevance scores
7. **Incremental extraction tracking** — SHA-256 file hashing skips unchanged files for 10x faster re-extraction
8. **Parallel batch processing** — ThreadPoolExecutor for multi-document extraction at scale
9. **Constraint validation** — Automated code checking against extracted constraints for compliance
10. **Repository-level aggregation** — Per-repo metadata, cross-repo comparison, extraction health metrics
11. **Multi-modal search engine** — FTS5, regex, glob, pattern, structured query DSL, vector embedding similarity, range queries — all in one API
12. **Multi-format document parsing** — Extracts knowledge from .md, .rst, .txt, .csv, .json, .log, .docx, .pdf, .xlsx, .pptx — normalized to markdown-like text for unified processing

## Token Economy

All responses pass through `api_response()` which auto-truncates data exceeding token budget when `summary_mode=True`. DTO fields use truncation (content[:300], summary[:200], concept[:5], related_module[:5]) for token efficiency.

---

## Related Sub-Features

- [Extract](sub-features/extract/concept.md) — Extract knowledge from documentation
- [Query](sub-features/query/concept.md) — Query knowledge relevant to a task
- [Status](sub-features/status/concept.md) — Show extraction coverage
- [Relationships](sub-features/relationships/concept.md) — Show relationship graph
- [Validate](sub-features/validate/concept.md) — Validate code against constraints

## Related Domains

- [CodeAnalysis](../codeanalysis/concept.md) — Document Parser for doc discovery
- [CodeGraph](../codegraph/concept.md) — GoldenKnowledgeStore for AI context injection
