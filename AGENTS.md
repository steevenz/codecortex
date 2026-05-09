# CodeCortex MCP Server

Agent instructions for working in this repository.

## Setup
- `uv sync` to install deps (lockfile: uv.lock).
- MCP config: Add to Claude Desktop config (`claude_desktop_config.json`):
  ```json
  {"mcpServers": {"codecortex": {"command": "uv", "args": ["--directory", "/path/to/codecortex", "run", "python", "-m", "src.main"]}}}
  ```
- Env: `CODECORTEX_DB_PATH`, `CODECORTEX_GRAPH_BACKEND` (kuzu/neo4j/falkordb), `CODECORTEX_MAX_REPOS` (default 50), `CODECORTEX_WEBHOOK_SECRET`, `OTEL_EXPORTER_OTLP_ENDPOINT`.

## Run
- Stdio: `python -m src.main` (registers 31 MCP tools).
- HTTP: Set `CODECORTEX_TRANSPORT=http`; serves at `http://127.0.0.1:8001/codecortex-api/v1/sync`.
- Webhook: POST `/webhook/git-event` triggers re-index on push/PR (requires `CODECORTEX_WEBHOOK_SECRET`).
- Docker test backends: `docker-compose up -d` (Neo4j + FalkorDB), then `pytest tests/test_backends_real.py -v`.

## Test
- Full suite: `pytest tests/ -v --override-ini="testpaths=tests" --ignore=tests/test_refactor_hardened.py`
- Production readiness: `python tests/test_production_readiness.py`
- Coverage: `pytest --cov=src/ tests/`
- Scope resolution: `pytest tests/test_scope_resolution.py -v`
- Backend integration: `pytest tests/test_backends_real.py -v` (requires Docker)
- Pre-commit hooks: `pre-commit install` then `pre-commit run --all-files`

## CI
- `.github/workflows/ci.yml` runs on push/PR: lint (pre-commit), pytest (coverage >90%), production readiness, state validation.

## Architecture
- DDD + Hexagonal: 6 domains (CodeRepository, CodeIndex, CodeGraph, Filesystem, CodeRefactor, CodeTester).
- Entry: `src/main.py` - `CortexOrchestrator` wires services via constructor DI.
- MCP Tools: Defined per-domain in `src/domain/*/api/tools.py`, registered in `main.py`.
- DB: SQLite (WAL) for metadata + Kuzu/Neo4j/FalkorDB for graph relationships.
- New: `multi_repo_sync` tool (track 50 repos), `git_audit` tool (secrets scan), webhook listener.
- Scope Resolution: `src/domain/codeindex/infrastructure/scope_resolution.py` — multi-pass cross-file reference resolver. Integrated into `CodeIndexService.index_repository()`.

## Key Features Implemented (GitNexus-derived)
- **Glob-based File Walker** (Filesystem) — replaces `os.walk` with concurrent batch stat
- **AST Cache** (CodeIndex) — LRU cache keyed by content hash
- **Leiden Community Detection** (CodeGraph) — with Louvain fallback
- **Global Registry & Staleness** (CodeRepository) — `~/.codecortex/registry.json`
- **Entry Point Scoring** (CodeGraph) — 0-100 score based on call ratio, naming, framework
- **In-Memory Knowledge Graph** (CodeGraph) — dual-index for O(1) lookups
- **Process Detection** (CodeGraph) — BFS execution flow tracing
- **Heritage Extraction** (CodeGraph) — class hierarchy extraction (Python/TS/Java/Go)
- **Import Resolution Pipeline** (CodeIndex) — per-language resolvers with suffix index
- **Framework Detection** (CodeIndex) — manifest + source pattern detection
- **Route Extraction** (CodeGraph) — FastAPI/Django/Flask/Express/Next.js route detection
- **ORM Dataflow** (CodeGraph) — SQLAlchemy/Django/Prisma model extraction
- **Worker Pool** (CodeIndex) — ThreadPoolExecutor for parallel parsing
- **Scope Resolution** (CodeIndex) — multi-pass cross-file reference resolution
- **TreeSitter 0.25.x API** — all 20+ language parsers compatible

## Security
- Path/URL validation on all tools (traversal prevention, SSRF guards).
- SSH Git auth via `auth_type="ssh"` (no tokens).
- Quotas: `CODECORTEX_MAX_REPOS=50`, `max_depth` (1-20), `max_file_size_mb=10`.
- Webhook signature verification via `X-Hub-Signature-256`.
- No auto-edit/commit without approval.
- Secrets in `.env` only (example in `.env.example`).
