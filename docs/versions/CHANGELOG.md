# CodeCortex Changelog

## [2026-05-05] Documentation Restructuring & Architecture Update

### Documentation
- **Restructured docs/** to align with Aegis Codeworks standards
  - Moved deprecated docs to `docs/drafts/archives/`
  - Rewrote `ARCHITECTURE.md` to reflect 6-domain architecture (CodeRepository, CodeIndex, CodeGraph, Filesystem, CodeRefactor, CodeTester)
  - Created new `docs/README.md` as module overview
  - Updated `docs/index.md` executive summary with current implementation
  - Updated `SECURITY.md` to reflect security utilities location (`src/domain/codegraph/core/security.py`)

### Architecture
- **6-Domain Structure**: Documentation now accurately reflects the current bounded contexts
  - Added Filesystem domain for file operations abstraction
  - Added CodeRefactor domain for safe code transformations
  - Added CodeTester domain for quality assurance capabilities
  - Updated dependency injection chain in `ARCHITECTURE.md`
  - Added technology stack rationale section

## [2026-05-03] Graphify Module Refinement (P0–P3)

### P0 — Critical Fixes

- **Logging Consistency** (`src/domain/graphify/service.py`)
  - Replaced `print(json.dumps(...))` in `_log_event()` with `src.core.logging_config.get_logger()`.
  - Matches `CodeGraphService` pattern — structured logs with domain prefix `CodeCortex.Domain.Graphify`.

- **Error Handling** (`src/domain/graphify/service.py:678`)
  - Bare `except Exception: pass` in `find_variable_usage_scope()` now logs warning with `exc_info=True`.
  - Partial `instances` results are returned instead of silently swallowed failures.

### P1 — Feature Porting

- **`suggest_questions()`** (`src/domain/graphify/service.py:1077`)
  - Ported from legacy `graphify/analyze.py`.
  - Cypher-based heuristics: ambiguous CALLS edges, isolated functions (degree = 0).
  - Returns `{type, question, why}` list.

- **`graph_diff()`** (`src/domain/graphify/service.py:1089`)
  - Ported from legacy `graphify/analyze.py`.
  - Returns snapshot stats per label: `{function: N, class: N, file: N, calls: N}`.

- **Security Guards** (new file: `src/domain/graphify/security.py`)
  - Ported from legacy `graphify/security.py`.
  - `validate_url()` — SSRF protection (scheme whitelist, private IP block, cloud metadata block).
  - `safe_fetch()` / `safe_fetch_text()` — guarded HTTP fetch with redirect re-validation, byte caps.
  - `validate_graph_path()` — directory-escape prevention.
  - `sanitize_label()` / `escape_html_label()` — control-char stripping + length cap.

### P2 — Performance Hardening

- **Security Scan Optimization** (`src/domain/graphify/service.py:126`)
  - Split `_audit_security_hygiene()` into two passes:
    1. Fast path: `name LIKE` (uses index on `symbols.name`).
    2. Slow path: `code LIKE` restricted to `symbol_type IN ('variable', 'function')` — skips Class/Module rows that lack a `code` field.
  - Deduplication via `seen_ids: set` prevents double-counting.

- **Fuzzy Search LIMIT Guard** (`src/domain/graphify/service.py:196`)
  - `_find_by_name_fuzzy_portable()` backend fetch reduced from **20,000** → **5,000** hard cap.
  - Client-side Levenshtein filtering unchanged; OOM risk reduced on large repositories.

### P3 — Community Detection

- **`find_community_surprises()`** (`src/domain/graphify/service.py:1106`)
  - Try-import chain: `networkx` → `python-louvain` → `leidenalg`.
  - Graceful fallback: missing libraries trigger `_find_bridge_surprises()` — a Cypher-based high-degree heuristic.
  - Cross-community CALLS edges ranked by confidence: `AMBIGUOUS (3) > INFERRED (2) > EXTRACTED (1)`.

### Wiring — Unified Pipeline

- **`GraphifyService.__init__`** (`service.py:49`)
  - Accepts optional `code_index_service` and `code_graph_service` (DI constructor injection).

- **`run_full_pipeline(repo_id)`** (`service.py:1202`)
  - 3-step orchestration: Index → Graph Build → Analysis.
  - Each step guarded by try/except; missing services log warning and skip.

- **MCP Tool Registration** (`tools.py`)
  - `run_full_pipeline`, `suggest_questions`, `graph_diff`, `find_community_surprises`.
  - Security utilities: `validate_url_safe`, `validate_graph_path_safe`, `sanitize_graph_label`.

- **Main Orchestrator** (`main.py`)
  - `CortexOrchestrator` wires all four services with bidirectional references.
  - Domain tool registrations (`register_codeindex_tools`, `register_codegraph_tools`, `register_graphify_tools`) connected to single `FastMCP` instance.

### Documentation

- `docs/architecture/architecture.md` — DI wiring, pipeline flow, backend abstraction.
- `docs/architecture/security.md` — SSRF guards, path validation, label sanitization reference.
- `docs/versions/changelog.md` — this file.
