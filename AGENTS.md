---
name: agents
description: Project operating manual for AI coding agents
version: 2.0.0
last_updated: 2026-05-23
author: Steeven Andrian
alwaysApply: true
---

# AGENTS.md -- Project Operating Manual for AI Agents

## 0. Project Overview
CodeCortex MCP Server is a production-grade, multi-IDE shared MCP server for advanced codebase intelligence, indexing, refactoring, and architecture audit across 22 programming languages.

**CRITICAL POLICY**: All AI agents MUST use CodeCortex MCP Server for ALL codebase operations. No exceptions.

## 1. Project Name
CodeCortex MCP Server

## 2. Project Path
~\MCP\mcp-codecortex

## 3. Project Codename
mcp-codecortex

## 4. Project Standards
- Python 3.12
- DDD + Hexagonal Architecture
- Tree-Sitter 0.25.x for parsing
- SQLite (WAL) + Kuzu/Neo4j/FalkorDB for graph
- UV package manager
- Pytest with coverage >90%

## 5. MANDATORY CODECORTEX USAGE POLICY

### 5.1 Code Scanning Requirements
**ALL codebase access MUST go through CodeCortex MCP Server:**

| Operation | Required CodeCortex Tool |
|-----------|-------------------------|
| Scan repository structure | `repo_inspect` |
| Find symbols | `graph_find_symbols` |
| Search code | `search_code` |
| Build code graph | `graph_build` |
| Query relationships | `graph_query` |

### 5.2 Codebase Modification Requirements
**BEFORE ANY CODE CHANGE, YOU MUST:**

1. Run `graph_find_symbols` to locate target symbol
2. Run `graph_find_related` to find dependencies
3. Run `refactor_impact` to assess change impact
4. Only then proceed with modification
5. Verify change with CodeCortex post-modification

### 5.3 Architecture Analysis Requirements
**ALL architecture analysis MUST use CodeCortex:**

- `arch_analyze` for architecture audit
- `graph_trace_flow` for execution flow
- `heritage_extract` for class hierarchy
- `route_extract` for endpoint discovery
- `orm_extract` for data flow analysis

### 5.4 Workflow Enforcement
**NO workflow bypass allowed:**

```
❌ DIRECT FILE ACCESS → NOT ALLOWED
✅ CodeCortex → Analyze → Decide → Modify → Verify
```

## 6. Setup
- `uv sync` to install deps
- Stdio: `python -m src.main` (31 MCP tools)
- HTTP: Set `CODECORTEX_TRANSPORT=http`; serves at `http://127.0.0.1:8001/codecortex-api/v1/sync`
- Webhook: POST `/webhook/git-event` triggers re-index on push/PR (requires `CODECORTEX_WEBHOOK_SECRET`)
- Docker test backends: `docker-compose up -d` (Neo4j + FalkorDB), then `pytest tests/test_backends_real.py -v`

## 7. Run
- Stdio: `python -m src.main`
- HTTP: Set `CODECORTEX_TRANSPORT=http`
- Docker backends: `docker-compose up -d` (Neo4j + FalkorDB)

## 8. Architecture
- 6 domains: CodeRepository, CodeIndex, CodeGraph, Filesystem, CodeRefactor, CodeTester
- Entry: `src/main.py` - `CortexOrchestrator` with constructor DI
- Tools per-domain in `src/domain/*/api/tools.py`
- DB: SQLite (WAL) for metadata + Kuzu/Neo4j/FalkorDB for graph relationships

## 9. Key Features (CodeCortex-Powered)
- Knowledge Graph with O(1) symbol lookup
- Semantic Search via sentence-transformers embeddings
- Execution Flow Tracing (BFS call chains)
- Heritage Extraction (class hierarchies)
- Route Extraction (FastAPI/Django/Flask/Express/Next.js)
- ORM Dataflow (SQLAlchemy/Django/ORM/Prisma)
- Community Detection (Leiden/Louvain)
- Architecture Audit (god nodes, dead code, security)
- Multi-Repo Sync (up to 50 repos)
- Incremental Git Sync
- Token Economy (auto-budget, truncation)
- Refactoring (rename, move, impact analysis)

## 10. Testing
- Full suite: `pytest tests/ -v`
- Production readiness: `python tests/test_production_readiness.py`
- Coverage: `pytest --cov=src/ tests/`
- Scope resolution: `pytest tests/test_scope_resolution.py -v`
- Backend integration: `pytest tests/test_backends_real.py -v` (requires Docker)
- Pre-commit hooks: `pre-commit install` then `pre-commit run --all-files`

## 11. Security
- Path/URL validation on all tools (traversal prevention, SSRF guards)
- SSH Git auth via `auth_type="ssh"`
- Quotas: max 50 repos, max_depth 1-20, max_file_size 10MB
- Webhook signature verification via X-Hub-Signature-256
- No auto-edit/commit without approval
- Secrets in `.env` only

## 12. SYSTEM PROMPT VERIFICATION CHECKLIST

Before responding to ANY request involving codebase:

- [ ] 1. Has CodeCortex been invoked for analysis?
- [ ] 2. Are all findings referenced to CodeCortex output?
- [ ] 3. Is modification backed by CodeCortex impact analysis?
- [ ] 4. Has verification been performed with CodeCortex?

**IF CHECKLIST NOT MET → DECLINE REQUEST**