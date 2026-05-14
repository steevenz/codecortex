---
name: agents
description: Project operating manual for AI coding agents
version: 1.0.0
last_updated: 2026-05-11
author: Steeven Andrian
alwaysApply: true
---

# AGENTS.md -- Project Operating Manual for AI Agents

## 0. Project Overview
CodeCortex MCP Server is a production-grade, multi-IDE shared MCP server for advanced codebase intelligence, indexing, refactoring, and architecture audit across 22 programming languages.

## 1. Project Name
CodeCortex MCP Server

## 2. Project Path
C:\Users\steevenz\MCP\mcp-codecortex

## 3. Project Codename
mcp-codecortex

## 4. Project Standards
- Python 3.12
- DDD + Hexagonal Architecture
- Tree-Sitter 0.25.x for parsing
- SQLite (WAL) + Kuzu/Neo4j/FalkorDB for graph
- UV package manager
- Pytest with coverage >90%

## 5. MUST use MCP
- Use MCP CodeCortex for code intelligence, codebase analysis, graph queries, refactoring, and architecture audit
- Use MCP Filesystem for file interactions
- Use MCP CCT for reasoning and thinking

## 6. Setup
- `uv sync` to install deps
- Stdio: `python -m src.main` (31 MCP tools)
- HTTP: `CODECORTEX_TRANSPORT=http` serves at `http://127.0.0.1:8001/codecortex-api/v1/sync`

## 7. Run
- Stdio: `python -m src.main`
- HTTP: Set `CODECORTEX_TRANSPORT=http`
- Docker backends: `docker-compose up -d` (Neo4j + FalkorDB)

## 8. Architecture
- 6 domains: CodeRepository, CodeIndex, CodeGraph, Filesystem, CodeRefactor, CodeTester
- Entry: `src/main.py` - `CortexOrchestrator` with constructor DI
- Tools per-domain in `src/domain/*/api/tools.py`

## 9. Key Features
- Knowledge Graph with O(1) symbol lookup
- Semantic Search via sentence-transformers embeddings
- Execution Flow Tracing (BFS call chains)
- Heritage Extraction (class hierarchies)
- Route Extraction (FastAPI, Django, Flask, Express, Next.js)
- ORM Dataflow (SQLAlchemy, Django ORM, Prisma)
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

## 11. Security
- Path/URL validation on all tools (traversal prevention, SSRF guards)
- SSH Git auth via `auth_type="ssh"`
- Quotas: max 50 repos, max_depth 1-20, max_file_size 10MB
- Webhook signature verification via X-Hub-Signature-256
- No auto-edit/commit without approval
- Secrets in `.env` only
