# How to Set Up CodeCortex MCP Server

Complete guide to installing, configuring, and connecting CodeCortex as an MCP (Model Context Protocol) server to your AI coding assistant.

## Overview

CodeCortex is a production-hardened MCP server that provides 27+ tools for code analysis, semantic indexing, architectural mapping, refactoring, and QA testing. It supports two transport modes:

| Transport | Use Case | Clients |
|-----------|----------|---------|
| **stdio** | IDE integration (default) | Claude Desktop, Cursor, Windsurf, Claude Code |
| **HTTP/SSE** | Remote or multi-client access | Any MCP-compatible client, custom integrations |

---

## Prerequisites

| Dependency | Version | Purpose |
|------------|---------|---------|
| **Node.js** | >= 18.0.0 | STDIO proxy server (multi-IDE lifecycle management) |
| **Python** | >= 3.10 | MCP server core and all analysis tools |
| **Git** | any | Repository sync and version control operations |

---

## Quick Start (3 Steps)

The fastest way to get CodeCortex running.

### Step 1: One-Command Setup

**Windows (PowerShell):**
```powershell
.\scripts\setup\quickstart.ps1
```

**macOS/Linux:**
```bash
bash scripts/setup/quickstart.sh
```

This script will:
1. Copy `.env.example` to `.env` (if not exists)
2. Install dependencies (`uv sync` or `pip install -e .`)
3. Generate a `CODECORTEX_CLIENT_API_KEY` automatically

### Step 2: Add to Your MCP Client

**Option A: NPX (Recommended — Auto-managed)**

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "npx",
      "args": ["-y", "codecortex"]
    }
  }
}
```

The NPX wrapper auto-handles: venv discovery, dependency sync, multi-IDE concurrency, graceful shutdown.

**Option B: Direct Python (No Node.js)**

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "python",
      "args": ["-u", "src/main.py"],
      "cwd": "C:/Users/steevenz/MCP/mcp-codecortex",
      "env": {
        "CODECORTEX_CLIENT_API_KEY": "your-key-here",
        "PYTHONPATH": "C:/Users/steevenz/MCP/mcp-codecortex"
      }
    }
  }
}
```

### Step 3: Restart Your IDE

Done. CodeCortex is ready. Try asking your AI: *"Analyze the codebase in /path/to/project"*.

---

## Manual Setup

If you prefer to understand each step, or the quickstart script doesn't work on your system.

### Step 1: Install Dependencies

**Using `uv` (fastest):**
```bash
uv sync
```

**Using `pip`:**
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

### Step 2: Configure Environment

```bash
# Copy template
cp .env.example .env

# Generate API key
python scripts/server/keygen.py --install
```

Your `.env` will now contain:
```env
CODECORTEX_CLIENT_API_KEY=codecortex_client_xxxx...
```

### Step 3: Configure MCP Client

Same as [Quick Start Step 2](#step-2-add-to-your-mcp-client).

---

## Client-Specific Configuration

### Claude Desktop

1. Open Claude Desktop → Settings → Developer → Edit Config
2. Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "npx",
      "args": ["-y", "codecortex"],
      "env": {
        "CODECORTEX_CLIENT_API_KEY": "your-key-here"
      }
    }
  }
}
```

3. Restart Claude Desktop

### Cursor

1. Settings → Cursor Settings → MCP
2. Click "Add New MCP Server"
3. Name: `codecortex`
4. Type: `command`
5. Command: `npx -y codecortex`
6. Restart Cursor

### Windsurf

1. Settings → MCP → Add Server
2. Name: `codecortex`
3. Command: `npx -y codecortex`
4. Restart Windsurf

### Claude Code (CLI)

```bash
claude mcp add codecortex -- npx -y codecortex
```

### VS Code (with MCP Extension)

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "codecortex": {
      "command": "npx",
      "args": ["-y", "codecortex"]
    }
  }
}
```

---

## Transport Modes

### STDIO (Default — IDE Integration)

Used when connecting via MCP clients like Claude Desktop, Cursor, etc.

```bash
# Via NPX (handles everything automatically)
npx codecortex

# Direct Python
python src/main.py
```

The Node.js proxy (`scripts/server/js/index.js`) manages:
- Automatic venv discovery and bootstrap
- Multi-IDE concurrency via file-lock mechanism
- Server lifecycle with reference counting
- Graceful shutdown on disconnect

### HTTP/SSE (Remote Access)

For scenarios requiring HTTP access or multiple simultaneous connections.

```bash
# Start HTTP server
python scripts/server/http.py

# Or via main.py with transport env
CODECORTEX_TRANSPORT=http python src/main.py
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CODECORTEX_HOST` | `127.0.0.1` | Server bind address |
| `CODECORTEX_PORT` | `8001` | Server port |
| `CODECORTEX_MCP_SECRET` | _(empty)_ | Optional secret path segment for multi-tenant safety |
| `CODECORTEX_CORS_ORIGINS` | `http://localhost,http://127.0.0.1` | Allowed CORS origins |

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Health check — server info, version, uptime |
| `/codecortex-api/v1/sync` | POST | JSON-RPC 2.0 MCP endpoint |
| `/codecortex-api/v1/sync` | GET | SSE streaming (keepalive + notifications) |
| `/docs` | GET | OpenAPI Swagger UI |
| `/redoc` | GET | ReDoc documentation |
| `/openapi.json` | GET | OpenAPI specification |

**With MCP Secret (multi-tenant):**

When `CODECORTEX_MCP_SECRET=mysecret` is set, the endpoints become:
- POST `/codecortex-api/v1/sync/mysecret`
- GET `/codecortex-api/v1/sync/mysecret`

**Example HTTP Request:**

```bash
curl -X POST http://127.0.0.1:8001/codecortex-api/v1/sync \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

## Available Tools

CodeCortex exposes 26 MCP tools across 6 domains:

### Repository (4 tools)

| Tool | Description |
|------|-------------|
| `repo_init` | Initialize a repository for analysis (syncs files to index) |
| `repo_inspect` | Inspect repository metadata and directory structure |
| `repo_analyze` | Full intelligence pipeline (init + index + analyze) |
| `repo_codemap` | Generate structured map of files and symbols |

> **Note:** Git operations (status, add, commit, push, pull, branch, etc.) are now handled by `fs_git` in the Filesystem domain.

### Filesystem (6 tools)

| Tool | Description |
|------|-------------|
| `fs_tree` | Get full directory tree from index (with git status enrichment) |
| `fs_read` | Read file content from repository (with git insights + status) |
| `fs_manage` | Write, append, delete, move, chmod, chown, symlink, touch, archive (zip/tar), xattr (extended attributes), and batch write operations |
| `fs_search` | Search files by name/content glob/regex with optional search-and-replace (dry-run by default) |
| `fs_git` | Comprehensive Git management: init, clone, status, add, commit, push, pull, fetch, branch, checkout, merge, rebase, log, diff, remote, tag, stash, reset, revert, cherry-pick |
| `fs_svn` | Comprehensive Subversion (SVN) management: checkout, update, commit, add, status, log, diff, info, revert, cleanup, lock, unlock, resolve, and more |

### Code Graph (7 tools)

| Tool | Description |
|------|-------------|
| `graph_find_symbols` | Find functions, classes, variables by name |
| `graph_query` | Query relationships (callers, callees, imports, hierarchy, etc.) |
| `graph_find_related` | Semantic cross-symbol search by natural language |
| `graph_build` | Build code relationship graph via Tree-sitter |
| `graph_trace_flow` | Trace execution flow from a symbol |
| `arch_analyze` | Full architectural analysis |
| `arch_audit` | Audit for god nodes, security issues, dead code, complexity |

### Code Index (2 tools)

| Tool | Description |
|------|-------------|
| `index_repo` | Index all files in a repository (AST symbol extraction) |
| `index_file` | Re-index a single file after changes |

### Code Refactor (4 tools)

| Tool | Description |
|------|-------------|
| `refactor_symbol` | Rename or move symbols with reference updates (includes rename + move) |
| `refactor_impact` | Predict blast radius of a refactor |
| `refactor_apply` | Apply refactoring recipes (docstrings, type hints, etc.) |

> **Note:** Text/regex search and replace is now handled by `fs_search` in the Filesystem domain. `refactor_rename` is deprecated — use `refactor_symbol(action="rename")` instead.

### Code Tester (2 tools)

| Tool | Description |
|------|-------------|
| `qa_run` | Run tests or linting (pytest, jest, go test, etc.) |
| `qa_status` | Poll status of a background QA task |

**Supported QA tools:** pytest, flake8, unittest, jest, phpunit, npm, pnpm, vitest, yarn, go_test, cargo_test, swift_test, kotlin_test, sbt_test, maven_test, ruby_test, flutter_test, dart_test, haskell_test, elixir_test, dotnet_test, perl_test, stylelint, ctest

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CODECORTEX_CLIENT_API_KEY` | Yes | — | API key for authentication |
| `CODECORTEX_DB_PATH` | No | `database/codecortex.db` | SQLite database path |
| `CODECORTEX_GRAPH_BACKEND` | No | `neo4j` | Graph backend: `neo4j`, `sqlite`, or `none` |
| `CODECORTEX_TRANSPORT` | No | `stdio` | Transport mode: `stdio`, `http`, or `sse` |
| `CODECORTEX_HOST` | No | `127.0.0.1` | HTTP server bind address |
| `CODECORTEX_PORT` | No | `8001` | HTTP server port |
| `CODECORTEX_MCP_SECRET` | No | _(empty)_ | Secret path segment for HTTP endpoint |
| `CODECORTEX_CORS_ORIGINS` | No | `http://localhost,http://127.0.0.1` | Comma-separated CORS origins |
| `CODECORTEX_CLIENT_INSTANCE_ID` | No | `codecortex-{hostname}-{pid}` | Client identifier for multi-IDE tracking |

---

## Typical Workflow

### 1. Initialize a Repository

```
repo_init(path="/path/to/your/project")
```

Returns a `repository_id` UUID for subsequent operations.

### 2. Index the Codebase

```
index_repo(repo_id="uuid-from-init")
```

Extracts symbols (functions, classes, variables) via Tree-sitter.

### 3. Analyze

```
repo_analyze(path="/path/to/your/project", dry_run=False)
```

One-shot: initializes, indexes, and returns full architectural analysis.

### 4. Query and Refactor

```
graph_find_symbols(search_term="UserService")
graph_query(query_type="callers", target="process_payment")
fs_search(repo_id="uuid", content_regex="TODO:", file_pattern="*.py")
fs_git(repo_path="/path/to/repo", subcommand="status", flags={"--short": True})
```

### 5. Run Tests

```
qa_run(repo_id="uuid", tool="pytest", background=True)
qa_status(task_id="task-uuid-from-qa-run")
```

---

## Troubleshooting

### "No API key found" / "CODECORTEX_CLIENT_API_KEY is required"

```bash
python scripts/server/keygen.py --install
```

Or manually add to `.env`:
```env
CODECORTEX_CLIENT_API_KEY=my-random-key-here
```

> **Note:** CodeCortex now uses only `CODECORTEX_CLIENT_API_KEY`. Legacy keys (`BOOTSTRAP_API_KEY`, `DASHBOARD_API_KEY`) have been removed.

### "ModuleNotFoundError: No module named 'xxx'"

Dependencies out of sync. Fix:
```bash
# With uv (recommended):
uv sync

# With pip:
pip install -e .
```

Common missing deps we've seen:
- `circuitbreaker` → `uv sync` fixes it
- `sqlalchemy` → `uv sync` fixes it  
- `pyyaml` → `uv sync` fixes it

### "Server failed to become ready"

1. Check Python version: `python --version` (requires >= 3.12)
2. Check `.venv` exists: `ls .venv/` or `.venv\Scripts\python --version`
3. Sync dependencies: `uv sync` (or `pip install -e .`)
4. Check logs in `outputs/logs/`
5. Ensure `.env` has `CODECORTEX_CLIENT_API_KEY`

### "Unknown method: tools/list" (HTTP 500)

The MCP lifecycle methods (`tools/list`, `tools/call`) weren't handled. This was a bug in `scripts/server/http.py` — update to latest version.

### "NameError: name 'uuid' is not defined"

Missing import in `scripts/server/http.py`. Update to latest version.

### "Shared server failed to become ready" with repeated EOF

Usually means Python server crashed during startup. Check the Python traceback in the error message — it typically points to a missing dependency.

### Multiple IDEs connecting

The shared proxy handles this automatically via reference counting. Each IDE gets its own stdio connection while sharing a single HTTP backend. No manual configuration needed.

### Port already in use

Set a different port:
```bash
# Windows:
$env:CODECORTEX_PORT=8010; npx codecortex
# macOS/Linux:
CODECORTEX_PORT=8010 npx codecortex
```

### Graph backend issues

Disable graph backend for SQLite-only mode:
```env
CODECORTEX_GRAPH_BACKEND=none
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    MCP Client                        │
│         (Claude Desktop, Cursor, Windsurf)           │
└──────────────────────┬──────────────────────────────┘
                       │ JSON-RPC 2.0 (stdio)
                       ▼
┌─────────────────────────────────────────────────────┐
│              Node.js Shared Proxy                    │
│  (scripts/server/js/index.js)                       │
│  • Auto venv bootstrap                               │
│  • Multi-IDE concurrency (file-lock)                 │
│  • Reference counting lifecycle                      │
│  • Graceful shutdown                                 │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP + SSE
                       ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI HTTP Server                     │
│  (scripts/server/http.py)                           │
│  • JSON-RPC 2.0 endpoint (/sync)                    │
│  • SSE streaming (/sync)                            │
│  • API key auth (X-API-KEY)                         │
│  • CORS, health check (/status)                     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              FastMCP Server Core                     │
│  (src/main.py)                                      │
│  • CortexOrchestrator                                │
│  • 27 registered tools across 6 domains              │
│  • SQLite + Neo4j backends                           │
│  • Tree-sitter AST parsing                           │
└─────────────────────────────────────────────────────┘
```
