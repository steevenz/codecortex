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

## Quick Start (NPX)

The fastest way to get started. No manual installation required.

### Step 1: Generate API Key

```bash
npx codecortex keygen
```

This generates a `CODECORTEX_BOOTSTRAP_API_KEY` and writes it to `.env`.

### Step 2: Add to Your MCP Client

Add this configuration to your client's MCP settings:

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

That's it. The NPX wrapper handles:
- Automatic Python venv creation
- Dependency installation
- Multi-IDE concurrency control
- Graceful shutdown and lifecycle management

---

## Manual Setup

For developers who want full control over the installation.

### Step 1: Clone and Install

```bash
cd mcp-codecortex

# Create Python virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Generate API Key

```bash
python scripts/server/keygen.py
```

Or manually create `.env` in the project root:

```env
CODECORTEX_BOOTSTRAP_API_KEY=your-generated-key-here
```

### Step 3: Configure MCP Client

**Option A: NPX (recommended)**

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

**Option B: Direct Python (no Node.js proxy)**

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "python",
      "args": ["-u", "src/main.py"],
      "cwd": "/absolute/path/to/mcp-codecortex",
      "env": {
        "CODECORTEX_BOOTSTRAP_API_KEY": "your-key-here",
        "PYTHONPATH": "/absolute/path/to/mcp-codecortex"
      }
    }
  }
}
```

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
        "CODECORTEX_BOOTSTRAP_API_KEY": "your-key-here"
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

CodeCortex exposes 27 MCP tools across 6 domains:

### Repository (6 tools)

| Tool | Description |
|------|-------------|
| `repo_init` | Initialize a repository for analysis (syncs files to index) |
| `repo_inspect` | Inspect repository metadata and directory structure |
| `repo_analyze` | Full intelligence pipeline (init + index + analyze) |
| `repo_codemap` | Generate structured map of files and symbols |
| `git_status` | Get Git working tree status |
| `git_commit` | Stage and commit changes |

### Filesystem (5 tools)

| Tool | Description |
|------|-------------|
| `fs_tree` | Get full directory tree from index |
| `fs_read` | Read file content from repository |
| `fs_write` | Write or overwrite a file (dry-run by default) |
| `fs_manage` | Delete or move files |
| `fs_glob` | List files matching a glob pattern |

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

### Code Refactor (5 tools)

| Tool | Description |
|------|-------------|
| `search_code` | Search code by text or regex |
| `search_replace` | Global find and replace (dry-run by default) |
| `refactor_symbol` | Rename or move symbols with reference updates |
| `refactor_impact` | Predict blast radius of a refactor |
| `refactor_apply` | Apply refactoring recipes (docstrings, type hints, etc.) |

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
| `CODECORTEX_BOOTSTRAP_API_KEY` | Yes | — | API key for authentication |
| `CODECORTEX_DASHBOARD_API_KEY` | No | — | Legacy API key (fallback) |
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
search_code(repo_id="uuid", query="TODO:")
```

### 5. Run Tests

```
qa_run(repo_id="uuid", tool="pytest", background=True)
qa_status(task_id="task-uuid-from-qa-run")
```

---

## Troubleshooting

### "No API key found"

Generate a key:
```bash
python scripts/server/keygen.py
```

Or manually add to `.env`:
```env
CODECORTEX_BOOTSTRAP_API_KEY=my-random-key-here
```

### "Server failed to become ready"

1. Check Python version: `python --version` (requires >= 3.10)
2. Check venv exists: `ls venv/` or `ls .venv/`
3. Check dependencies: `pip install -r requirements.txt`
4. Check logs in `outputs/logs/`

### Multiple IDEs connecting

The shared proxy handles this automatically via reference counting. Each IDE gets its own stdio connection while sharing a single HTTP backend. No manual configuration needed.

### Port already in use

Set a different port:
```bash
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
