# CodeCortex Support Matrix

> **Version:** 0.1.0
> **Last Updated:** 2026-05-09
> **Covers:** Languages, frameworks, MCP, LLMs, OS, databases, graph backends, QA tools, CI/CD, IDEs

---

## 1. Programming Languages (Tree-Sitter Parsing)

Full AST parsing, symbol extraction, and code analysis using Tree-Sitter 0.25.x.

| Language | Parser Status | Functions | Classes | Imports | Variables | Scope Resolution | Heritage |
|----------|:------------:|:---------:|:-------:|:-------:|:---------:|:---------------:|:--------:|
| Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| TypeScript | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| JavaScript | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| JSX/TSX | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Go | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Rust | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Java | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kotlin | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| PHP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ruby | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Swift | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Dart/Flutter | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| C++ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| C# | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Elixir | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Haskell | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Perl | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Lua | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Zig | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Bash | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| SQL | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

**Legend:** ✅ = Full support, ❌ = Not applicable or not yet implemented

---

## 2. Framework Detection

Automatic detection of web frameworks during indexing. Enables framework-aware analysis (route extraction, component tagging).

| Framework | Language | Detection Method | Route Extraction | Component Detection |
|-----------|:--------:|------------------|:----------------:|:-------------------:|
| **Next.js** | TypeScript/JS | File patterns (`pages/`, `app/`), `'next'` imports, `getServerSideProps` | ✅ | ✅ |
| **React** | TypeScript/JS | `from 'react'`, JSX, hooks | ❌ | ✅ |
| **Flutter** | Dart | `from 'flutter'`, `extends StatelessWidget/StatefulWidget` | ❌ | ✅ |
| **Laravel** | PHP | File structure, facades, `Illuminate` namespace | ❌ | ✅ |
| **FastAPI** | Python | `@app.get/post/...` decorators, `from fastapi import` | ✅ | ❌ |
| **Django** | Python | `from django import`, `models.Model` inheritance | ✅ | ✅ |
| **Flask** | Python | `@app.route(...)` | ✅ | ❌ |
| **Express** | JavaScript/TS | `require('express')`, `app.get/post/...` | ✅ | ❌ |

---

## 3. Route Extraction

HTTP route detection from web frameworks.

| Framework | URL Path | HTTP Method | Handler | Middleware | Response Model |
|-----------|:--------:|:-----------:|:-------:|:----------:|:--------------:|
| **FastAPI** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Django** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Flask** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Express** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Next.js (pages)** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Next.js (app)** | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## 4. ORM Dataflow Detection

| ORM | Language | Model Extraction | Field Types | Relationships | Query Detection |
|-----|:--------:|:----------------:|:-----------:|:-------------:|:---------------:|
| **SQLAlchemy** | Python | ✅ | ✅ | ✅ | ✅ |
| **Django ORM** | Python | ✅ | ✅ | ✅ | ✅ |
| **Prisma** | TypeScript | ✅ | ✅ | ✅ | ❌ |

---

## 5. Heritage Extraction (Class Hierarchy)

| Language | Parent Classes | Child Classes | Mixins | Interface Impl. |
|----------|:--------------:|:-------------:|:------:|:----------------:|
| Python | ✅ | ✅ | ✅ | ❌ |
| TypeScript | ✅ | ✅ | ❌ | ✅ |
| JavaScript | ✅ | ✅ | ❌ | ❌ |
| Java | ✅ | ✅ | ❌ | ✅ |
| Go | ✅ (embedding) | ❌ | ❌ | ✅ |
| C++ | ✅ | ✅ | ❌ | ✅ |
| C# | ✅ | ✅ | ❌ | ✅ |
| PHP | ✅ | ✅ | ✅ | ✅ |
| Dart | ✅ | ✅ | ❌ | ✅ |
| Kotlin | ✅ | ✅ | ❌ | ✅ |

---

## 6. Import Resolution

| Language | Relative Imports | Absolute Imports | Wildcard Imports | Re-exports |
|----------|:----------------:|:-----------------:|:----------------:|:----------:|
| Python | ✅ | ✅ | ✅ | ✅ |
| TypeScript/JS | ✅ | ✅ | ❌ | ✅ |
| Go | ✅ | ✅ | ❌ | ❌ |
| Rust | ✅ | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ❌ | ❌ |
| PHP | ✅ | ✅ | ❌ | ✅ |
| Dart | ✅ | ✅ | ❌ | ✅ |

---

## 7. MCP Transport Support

| Transport | Protocol | Status | Use Case |
|-----------|:--------:|:------:|----------|
| **STDIO** | JSON-RPC over stdin/stdout | ✅ | Default. Claude Desktop, Cursor, local tools |
| **SSE** | Server-Sent Events | ✅ | Web-based MCP clients, streaming |
| **HTTP/JSON-RPC** | HTTP POST | ✅ | Custom integrations, webhooks, CI/CD |

---

## 8. LLM / AI Client Support

CodeCortex speaks the **Model Context Protocol (MCP)** natively. Compatible with any MCP-compatible AI client.

| Client | MCP Support | Works With | Notes |
|--------|:-----------:|:----------:|-------|
| **Claude Desktop** | ✅ | ✅ | Primary target. STDIO transport |
| **Claude Code (CLI)** | ✅ | ✅ | Via MCP config |
| **Cursor** | ✅ | ✅ | Add MCP server in Cursor settings |
| **Windsurf** | ✅ | ✅ | Via `.windsurf` MCP configuration |
| **Cline (VS Code)** | ✅ | ✅ | MCP server config |
| **Trae** | ✅ | ✅ | MCP server config |
| **Continue (VS Code/JetBrains)** | ✅ | ✅ | Open-source MCP client |
| **Custom LLM apps** | ✅ | ✅ | Any app using MCP SDK |

---

## 9. Operating System Support

| OS | Status | Notes |
|----|:------:|-------|
| **Windows** | ✅ | Primary development target. ASCII-safe CLI output (no Unicode) |
| **macOS** | ✅ | Full support via `uv` + Python |
| **Linux** | ✅ | Full support. Docker-compose for graph backends |

---

## 10. Database Support

| Database | Type | Usage | Status |
|----------|:----:|-------|:------:|
| **SQLite** | Embedded (WAL mode) | Primary metadata store. All symbol data, files, commits | ✅ |
| **Kuzu** | Embedded columnar graph | Optional graph backend. Cypher subset | ✅ |
| **Neo4j** | Client-server graph | Optional graph backend. Full Cypher | ✅ |
| **FalkorDB** | In-memory Redis graph | Optional graph backend. Low-latency | ✅ |

**Persistence Strategy:**
- SQLite is **always** used (mandatory) — stores all symbols, files, edges, commits
- Graph backend (Kuzu/Neo4j/FalkorDB) is **optional** — stores graph nodes/edges for complex graph queries
- Fallback: if no graph backend configured, graph queries run against SQLite edges table

---

## 11. Graph Backend Comparison

| Feature | Kuzu | Neo4j | FalkorDB | SQLite (fallback) |
|---------|:----:|:-----:|:--------:|:-----------------:|
| Setup | Auto (pip package) | Docker required | Docker required | Built-in |
| Query Language | Cypher subset | Full Cypher | RedisGraph | SQL |
| Graph Algorithm Support | Limited | Full (GDS library) | Limited | Basic |
| Performance (local) | Fast | Moderate | Fast | Fast (simple queries) |
| Performance (large graphs) | Excellent | Excellent | Excellent | Degrades |
| Persistence | Disk (columnar) | Disk | Memory + snapshot | Disk |
| Concurrent Access | Single-process | Multi-client | Multi-client | Single-process |

---

## 12. QA / Testing Tool Support

| Tool | Type | Status | Notes |
|------|:----:|:------:|-------|
| **pytest** | Python test runner | ✅ | Primary test framework |
| **unittest** | Python test runner | ✅ | |
| **flake8** | Python linter | ✅ | |
| **jest** | JS/TS test runner | ✅ | |
| **vitest** | JS/TS test runner | ✅ | |
| **npm** | JS package scripts | ✅ | Supports `npm test`, `npm run lint` |
| **pnpm** | JS package scripts | ✅ | |
| **yarn** | JS package scripts | ✅ | |
| **phpunit** | PHP test runner | ✅ | |
| **go_test** | Go test runner | ✅ | |
| **cargo_test** | Rust test runner | ✅ | |
| **swift_test** | Swift test runner | ✅ | |
| **kotlin_test** | Kotlin test runner | ✅ | |
| **sbt_test** | Scala test runner | ✅ | |
| **maven_test** | Java/Maven test runner | ✅ | |
| **ruby_test** | Ruby test runner | ✅ | |
| **flutter_test** | Flutter test runner | ✅ | |
| **dart_test** | Dart test runner | ✅ | |
| **haskell_test** | Haskell test runner | ✅ | |
| **elixir_test** | Elixir test runner | ✅ | |
| **dotnet_test** | .NET test runner | ✅ | |
| **perl_test** | Perl test runner | ✅ | |
| **stylelint** | CSS/SCSS linter | ✅ | |
| **ctest** | CMake test runner | ✅ | |

---

## 13. CodeCortex Internal Test Suite

| Test Area | Coverage | Status |
|-----------|:--------:|:------:|
| **Backend Integration** (Neo4j, FalkorDB) | 10+ tests | ✅ (requires Docker) |
| **Database Cleanup** (compact, cleanup) | 3 tests | ✅ |
| **Takeout/Import** (export, import) | 4 tests | ✅ |
| **Token Economy** (estimation, cache, budget) | 9 tests | ✅ |
| **CLI** (version, help, list, batch, audit) | 7 tests | ✅ |
| **Scope Resolution** | 5+ tests | ✅ |
| **Production Readiness** | 15+ tests | ✅ |
| **Code Indexing** | 20+ tests | ✅ |
| **Graph Analysis** | 15+ tests | ✅ |

---

## 14. CI/CD Support

| Platform | Status | Notes |
|----------|:------:|-------|
| **GitHub Actions** | ✅ | `.github/workflows/ci.yml` — lint, test (coverage >90%), production readiness, state validation |

---

## 15. File Classification

When indexing, files are automatically classified:

| Classification | Extension Examples | Included in Index |
|:--------------:|-------------------|:-----------------:|
| **code** | `.py`, `.ts`, `.js`, `.go`, `.rs`, `.java`, etc. | ✅ AST parsed |
| **doc** | `.md`, `.rst`, `.txt`, `.pdf`, `.docx` | ✅ Content indexed |
| **config** | `.json`, `.yaml`, `.toml`, `.ini`, `.cfg` | ✅ Content indexed |
| **binary** | `.exe`, `.dll`, `.so`, `.dylib`, `.png`, `.jpg` | ❌ Skipped |
| **other** | `.csv`, `.log`, `.sql` | ✅ Content indexed |

---

## 16. Security & Validation

| Guard | Enforced | Description |
|-------|:--------:|-------------|
| Path traversal prevention | ✅ | Rejects `..` and absolute paths in file operations |
| SSRF prevention | ✅ | Only local file paths accepted, not URLs |
| UUID validation | ✅ | All `repo_id`, `file_id` must be valid UUIDs |
| Label sanitization | ✅ | Graph labels sanitized for XSS/NoSQL injection |
| Depth limiting | ✅ | `max_depth` clamped to 1-20 |
| Dry-run default | ✅ | All destructive operations default to preview mode |
| Quota enforcement | ✅ | `CODECORTEX_MAX_REPOS` (default 50) |
| Webhook signature verification | ✅ | `X-Hub-Signature-256` for webhook events |
| No auto-edit/commit | ✅ | Requires explicit user approval |
| Secrets in `.env` only | ✅ | `.env.example` as template, `.env` in `.gitignore` |

---

*This document follows Aegis Codeworks documentation standards. Update when new language, framework, or backend support is added.*
