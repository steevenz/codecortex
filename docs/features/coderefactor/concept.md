# CodeRefactor: Safe Code Transformation

> **Domain:** CodeRefactor
> **Package:** `src/modules/coderefactor/`
> **Version:** 2.0.0
> **AI Coder Impact:** 10/10 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

CodeRefactor is the **autonomous refactoring engine** — enables AI agents to perform safe, semantic code transformations (rename, move, extract, inline, signature changes, file operations, modularize) with full blast radius analysis, multi-language support (16 languages), and git-backed safety. It provides 1 unified MCP tool with 12 actions for symbol-level and VCS-level transformations.

## Why This Exists

- **AI Autonomy:** AI agents can refactor code without manual tracking of dependencies
- **Safety Guarantees:** Blast radius analysis prevents cascading breakage
- **Multi-Language Support:** 16 languages with Tree-Sitter semantic understanding
- **Git Integration:** Auto-commit with descriptive messages for rollback
- **Dry-Run Safety:** Preview changes before applying them
- **Auto-Reindex:** Knowledge graph updated post-mutation — no stale data

## Theoretical Foundation

- **AST Parsing:** Tree-Sitter for accurate symbol extraction across 16 languages
- **Knowledge Graph:** Dependency graph for blast radius and transitive analysis
- **Git VCS:** Commit-based safety with rollback capability
- **Diff Generation:** Unified diff for change preview
- **Multi-Language Import Updates:** Generic updater for Python, JS/TS, Go, PHP, Rust
- **Smart Placement Detection:** Optimal insertion position for moved code elements
- **DDD Modularization:** AI-assisted domain clustering for monolith splits

## Architecture

```
src/modules/coderefactor/
├── api/              → tools.py: 1 unified MCP tool (12 actions), cli.py: CLI commands
├── services/         → Service classes: DI via constructor, pure use-cases
│   └── refactor.py  → Refactor orchestration with 12 actions
├── core/            → dtos.py: typed DTOs (RefactorResult, RefactorChange, BlastRadius, RefactorErrorCode)
└── utils/           → Helper methods for AST parsing, import updates, diff generation
```

## Domain Boundary

- **Owns:** `code_refactor` (unified tool with 12 actions)
- **Does NOT own:** `code_analyze`, `code_search`, `code_audit` (handled by codeanalysis domain)
- **Depends on:** `DatabaseManager`, `FilesystemService`, `Git`, `Graph`
- **Consumed by:** MCP layer via `api/tools.py`

## CLI Architecture Note

The CLI domain is named `codebase` (not `coderefactor`) as an intentional UX decision. This provides a unified interface for codebase operations across multiple domains (codeanalysis, codegraph, codeindex, codetester, coderefactor). Users access all codebase operations via `codecortex cb <command>`.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `services/` + `core/` separation
- **DI:** Constructor injection for all services
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Guard clauses, structured errors with RefactorErrorCode
- **Logging:** `CodeCortex.Domain.Refactor` logger namespace
- **Documentation:** All docs in `docs/features/coderefactor/`

## Error Codes

| Prefix | Action |
|--------|--------|
| REF_0xx | impact |
| REF_1xx | rename |
| REF_2xx | move |
| REF_3xx | change_signature |
| REF_4xx | extract_function |
| REF_5xx | inline_function |
| REF_6xx | rename_file |
| REF_7xx | rename_folder |
| REF_8xx | move_file |
| REF_9xx | modularize |
| REF_5xx | Internal error |

## 10/10 AI Coder Impact Features

1. **Blast Radius Analysis** — Full impact analysis with direct + transitive callers
2. **Multi-Language Support** — 16 languages with Tree-Sitter semantic understanding
3. **Smart Placement Detection** — Optimal insertion position for moved code
4. **Multi-Language Import Updates** — Generic updater for Python, JS/TS, Go, PHP, Rust
5. **Dry-Run Safety** — Preview changes before applying them
6. **Git Integration** — Auto-commit with descriptive messages for rollback
7. **Auto-Reindex** — Knowledge graph updated post-mutation
8. **DDD Modularization** — AI-assisted domain clustering for monolith splits
9. **Full Signature Changes** — Add/remove/reorder parameters with call site updates
10. **Nested Import Detection** — Per-file blast radius for folder renames

---

## Related Sub-Features

- [Impact Analysis](sub-features/impact/concept.md)
- [Rename](sub-features/rename/concept.md)
- [Move](sub-features/move/concept.md)
- [Change Signature](sub-features/change_signature/concept.md)
- [Extract Function](sub-features/extract_function/concept.md)
- [Inline Function](sub-features/inline_function/concept.md)
- [Rename File](sub-features/rename_file/concept.md)
- [Rename Folder](sub-features/rename_folder/concept.md)
- [Move File](sub-features/move_file/concept.md)
- [Modularize](sub-features/modularize/concept.md)
