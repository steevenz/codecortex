# CodeIndex: Semantic Code Indexing

> **Domain:** CodeIndex
> **Package:** `src/modules/codeindex/`
> **Version:** 2.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

CodeIndex is the **foundational semantic data layer** — transforms raw source code into structured, queryable data (symbols, imports, relationships) that powers CodeGraph (graph relationships), CodeAnalysis (symbol search, analysis), CodeRefactor (rename, move), and CodeTester (test discovery). It provides 6 MCP tools for indexing, status checking, incremental updates, and export.

Without CodeIndex:
- CodeGraph has no symbols to graph
- CodeRefactor has no references to rename
- CodeAnalysis has no symbol table to query
- CodeTester cannot discover test files

## Why This Exists

- **AST > Regex:** Regular expressions cannot understand nested scopes, resolve qualified names, or distinguish between a function definition and a call. Tree-Sitter produces a concrete syntax tree matching the language parser.
- **Class Hierarchy:** Methods nested inside classes get `parent_id` linking them to their parent class — queriable via `symbols.parent_id` FK chain. INHERITS edges connect methods to their parent class; CLASS_INHERITS edges connect classes to their base classes.
- **Cross-File Edges:** `_resolve_edges_sqlite()` builds 4 edge types from symbol metadata:
  - `CALLS` — caller to callee across files
  - `INHERITS` — method to parent class
  - `CLASS_INHERITS` — class to base class
  - `IMPORTS` — file to imported symbol
- **Language Agnosticism:** 35+ languages through a unified parsing API — one pipeline, many grammars.
- **Fallback Chain:** Tree-Sitter primary → Python `ast` builtin fallback → generic TS parser for niche languages.
- **VCS-Aware Incremental:** Git and SVN support for differential re-indexing with transparent fallback reporting.
- **Configurable Performance:** Tunable file size limits, parse timeouts, and concurrency via environment variables.

## Theoretical Foundation

- **Tree-Sitter:** Incremental, error-tolerant parsing. Unlike ANTLR or hand-written parsers, Tree-Sitter can parse incomplete or syntactically invalid files (common during development) and still produce a useful CST/AST.
- **Abstract Syntax Tree (AST):** A tree representation of source code where each node is a syntactic construct (function definition, variable declaration, class declaration), omitting semicolons, whitespace, and other purely syntactic tokens.
- **Symbol Resolution:** The process of mapping a name reference to its definition, accounting for scope boundaries, imports, and declaration order. CodeIndex runs multi-pass scope resolution after parsing all files.
- **Worker Pool:** CPU-bound Tree-Sitter parsing parallelized via `ThreadPoolExecutor`. For repos <15 files or <512KB total, sequential async path is used to avoid overhead.
- **VCS Detection:** Automatic detection of Git (.git) and SVN (.svn) working copies for incremental indexing.
- **SHA-256 Hashing:** File content hashing for cache invalidation and change detection.

## Architecture

```
src/modules/codeindex/
├── api/              → tools.py: 6 MCP tools (status, index, incremental, files, pre_scan, export), cli.py: CLI commands (ci domain)
├── services/         → Service classes: DI via constructor, pure use-cases
│   ├── indexer.py   → Indexer service with AST parsing, framework enrichment, graph sync
│   ├── framework_detection.py → Framework pattern detection and enrichment
│   └── pre_scan.py   → Python import pre-scanning for cross-file resolution
├── core/            → dtos.py: typed DTOs for all public interfaces
└── parsers/          → Tree-Sitter parsers, language-specific strategies, framework modules
```

## Domain Boundary

- **Owns:** `code_index` (6 actions: status, index, incremental, files, pre_scan, export)
- **Does NOT own:** `code_refactor` (handled by coderefactor domain), `code_graph` (handled by codegraph domain)
- **Depends on:** `DatabaseManager`, `FilesystemService`, `RepositoryService`
- **Consumed by:** MCP layer via `api/tools.py`, CLI via `api/cli.py`

## CLI Architecture Note

The CLI domain is named `codeindex` with alias `ci` — provides direct CLI access to indexing operations. Users access CodeIndex operations via `codecortex ci <command>`.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `services/` + `core/` separation
- **DI:** Constructor injection for all services
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Guard clauses, structured errors with CI_001-CI_007 error codes
- **Logging:** `CodeCortex.Domain.CodeIndex.*` logger namespace
- **Documentation:** All docs in `docs/features/codeindex/`

## Coverage: 35+ Languages

| Category | Count | Languages |
|----------|-------|-----------|
| Dedicated Tree-Sitter | 27 | Python, JavaScript, TypeScript, TSX, Go, Rust, C++, C, Java, Ruby, C#, PHP, Kotlin, Scala, Swift, Haskell, Dart, Perl, Elixir, R, Solidity, Svelte, TOML, SQL, GraphQL, HCL, Astro |
| Generic Tree-Sitter | 6 | Julia, Lua, Objective-C, PowerShell, Verilog, Zig |
| Non-TS (Regex-based) | 2 | Vue, Cobol |

All parsers produce the standard output format with `functions[]`, `classes[]`, `variables[]`, `imports[]`, `function_calls[]`, `args`, `class_context`, and `bases`.

## Edge Types (4 Relations)

| Type | Source | Target | Created By |
|------|--------|--------|------------|
| `CALLS` | Function/method | Called function | `_resolve_edges_sqlite()` from function_calls metadata |
| `INHERITS` | Method | Parent class | `_resolve_edges_sqlite()` from `parent_id` chain |
| `CLASS_INHERITS` | Class | Base class | `_resolve_edges_sqlite()` from class `signature` (bases) |
| `IMPORTS` | File sentinel | Imported symbol | `_resolve_edges_sqlite()` from `__file__` symbol metadata JSON |

## Framework Detection (15+ Frameworks)

| Framework | Detection Signals |
|-----------|------------------|
| Next.js | `next.config.js`, `app/` directory, `next/image`, `next/link` imports |
| Flutter | `pubspec.yaml`, `lib/` directory, `import 'package:flutter'` |
| Laravel | `routes/web.php`, `app/` directory, `Illuminate` namespace |
| React | `package.json` with `react`, `.jsx` files, `useState`, `useEffect` |
| Vue | `package.json` with `vue`, `.vue` files, `createApp`, `defineComponent` |
| Angular | `angular.json`, `.ts` files, `@angular/core` imports, `@Component` decorator |
| Django | `settings.py`, `models.py`, `from django.db import models` |
| Rails | `Gemfile`, `app/` directory, `class ApplicationRecord < ApplicationRecord` |
| Express | `package.json` with `express`, `app.use()`, `express.Router()` |
| NestJS | `package.json` with `@nestjs/common`, `@Controller`, `@Injectable` |
| Symfony | `composer.json`, `src/` directory, `Symfony\Component` namespace |
| ASP.NET Core | `.csproj`, `Controllers/` directory, `Microsoft.AspNetCore` namespace |
| SvelteKit | `.svelte` files, `+page.svelte`, `svelte/` imports, `@sveltejs/kit` |
| SolidJS | `solid-js` dependency, `createSignal`, `createEffect`, `createMemo` |
| Tauri | `tauri.conf.json`, `src-tauri/` directory, `use tauri::`, `@tauri-apps/` imports |
| Astro | `.astro` files, `astro.config.*`, `astro:` imports, `astro` dependency |

## Error Codes

| Prefix | Tool |
|--------|------|
| CI_001 | code_index (invalid action) |
| CI_002 | code_index (missing repo_id) |
| CI_003 | code_index (path validation failed) |
| CI_004 | code_index (incremental missing repo_id) |
| CI_005 | code_index (files missing repo_id or files list) |
| CI_006 | code_index (files list empty) |
| CI_007 | code_index (export missing repo_id) |
| CI_500 | code_index (internal error) |

## 10/10 AI Coder Impact Features

1. **VCS-Aware Incremental:** Git and SVN support with transparent fallback reporting and vcs_type detection
2. **Configurable Performance:** Tunable file size limits (CODECORTEX_MAX_FILE_SIZE_MB), parse timeouts (CODECORTEX_PARSE_TIMEOUT_SECONDS), and concurrency (CODECORTEX_MAX_CONCURRENT_INDEXING)
3. **Index Export:** Export symbol table as structured JSON with configurable limits (action="export")
4. **CLI Access:** Full CLI domain (ci) with 6 commands for terminal-based operations
5. **Enhanced Framework Detection:** 4 new frameworks (SvelteKit, SolidJS, Tauri, Astro) with dedicated detection modules
6. **Expanded Language Support:** 8 new languages (R, Solidity, Svelte, TOML, SQL, GraphQL, HCL, Astro) for 35+ total
7. **Metrics Reporting:** symbols_per_sec, files_per_sec, edge_count, languages, and active config in status response
8. **Transparent Fallback:** Incremental indexing reports vcs_type, fallback_to_full_sync, and fallback_reason
9. **Service Layer Abstraction:** All DB access moved to service layer (get_index_status, export_index) for clean architecture
10. **Path Validation:** Explicit path validation with SSRF guards and traversal prevention

## Token Economy

All responses pass through `api_response()` which auto-truncates data exceeding token budget when `summary_mode=True`.

---

## Related Sub-Features

- [Tree-Sitter Parsing](sub-features/tree-sitter-parsing/concept.md)
- [Framework Detection](sub-features/framework-detection/concept.md)
- [Scope Resolution](sub-features/scope-resolution/concept.md)
- [AST Cache](sub-features/ast-cache/concept.md)
- [Worker Pool](sub-features/worker-pool/concept.md)
- [Import Resolution](sub-features/import-resolution/concept.md)
- [Semantic Search](sub-features/semantic-search/concept.md)

## Tool Reference

### code_index

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | ✅ | — | `status` / `index` / `incremental` / `files` / `pre_scan` / `export` |
| `repo_id` | string | ❌ | — | Repository UUID (required for status/incremental/files/export) |
| `path` | string | ❌ | — | Repository root path (auto-resolves repo_id when needed for index/pre_scan) |
| `files` | list | ❌ | — | List of relative file paths for action="files" |

**Actions:**
- `status` — Check indexing status (symbol/file/edge count, languages, last indexed, active config)
- `index` — Full re-index a repository (AST parse all files)
- `incremental` — Index only files changed since last index (git diff for Git, svn status for SVN)
- `files` — Index specific files by relative path
- `pre_scan` — Pre-scan Python imports for cross-file call resolution
- `export` — Export symbol table as structured JSON (symbols, edges, files) with configurable limit

**Output (status):**
```json
{
  "repo_id": "uuid",
  "symbol_count": 1234,
  "file_count": 45,
  "edge_count": 2345,
  "last_indexed_at": "2026-05-29T00:00:00Z",
  "root_path": "/path/to/repo",
  "languages": {"python": 30, "javascript": 15},
  "config": {
    "max_file_size_mb": 5,
    "parse_timeout_seconds": 15,
    "max_concurrent_indexing": 10
  }
}
```

**Output (incremental):**
```json
{
  "repo_id": "uuid",
  "changed_files": ["src/service.py"],
  "files_changed": 1,
  "vcs_type": "git",
  "fallback_to_full_sync": false,
  "fallback_reason": null,
  "duration_s": 0.5
}
```

**Output (export):**
```json
{
  "repo_id": "uuid",
  "symbol_count": 500,
  "file_count": 45,
  "edge_count": 1000,
  "truncated": false,
  "limit_applied": 500,
  "symbols": [...],
  "files": [...],
  "edges": [...]
}
```

---

## CLI Commands

| Command | Usage | Description |
|---------|------|-------------|
| `codecortex ci status --repo-id <uuid>` | Check indexing status |
| `codecortex ci index --path /repo` | Full re-index of repository |
| `codecortex ci index --repo-id <uuid>` | Full re-index by UUID |
| `codecortex ci incremental --repo-id <uuid>` | Incremental re-index (Git/SVN-aware) |
| `codecortex ci files --repo-id <uuid> src/a.py src/b.py` | Index specific files |
| `codecortex ci pre_scan --repo-id <uuid>` | Pre-scan Python imports |
| `codecortex ci pre_scan --path /repo` | Pre-scan by path |
| `codecortex ci export --repo-id <uuid>` | Export symbol table to stdout |
| `codecortex ci export --repo-id <uuid> --limit 1000 --output symbols.json` | Export to file with custom limit |
