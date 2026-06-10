# CodeCortex MCP - NPX Setup Guide

## Overview

CodeCortex MCP Server can now be installed and used via **npx** for seamless integration with any IDE that supports MCP (Model Context Protocol).

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Run the Server

```bash
# Method 1: Using npx (after npm link or global install)
npx codecortex-mcp

# Method 2: Using Node.js directly
node scripts/server/run_server.js

# Method 3: Using Python directly
uv run python -m src.main
```

## IDE Configuration

### Claude Desktop / Trae IDE

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "npx",
      "args": ["codecortex-mcp"],
      "env": {
        "CODECORTEX_DB_PATH": "${HOME}/.codecortex/db.sqlite",
        "CODECORTEX_GRAPH_BACKEND": "kuzu",
        "CODECORTEX_MAX_REPOS": "50"
      }
    }
  }
}
```

### VS Code (using MCP extension)

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["scripts/server/run_server.js"],
      "env": {
        "CODECORTEX_DB_PATH": "./database/codecortex.db",
        "CODECORTEX_GRAPH_BACKEND": "kuzu"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODECORTEX_DB_PATH` | `~/.codecortex/db.sqlite` | Path to SQLite database |
| `CODECORTEX_GRAPH_BACKEND` | `kuzu` | Graph database backend (kuzu/neo4j/falkordb) |
| `CODECORTEX_MAX_REPOS` | `50` | Maximum repositories to track |
| `CODECORTEX_TRANSPORT` | `stdio` | Transport mode (stdio/http) |

## Available Tools (37 total)

### CodeGraph (7 tools)
- `graph_find_symbols` - Find functions, classes, variables
- `graph_query` - Query relationships in code
- `graph_build` - Build code graph
- `arch_analyze` - Architecture audit
- `heritage_extract` - Class hierarchy extraction
- `graph_find_related` - Find related symbols
- `trace_flow` - Execution flow tracing

### CodeIndex (3 tools)
- `index_repository` - Index a repository
- `index_file` - Index a single file
- `framework_detection` - Detect framework

### CodeRepository (5 tools)
- `repo_inspect` - Inspect repository
- `repo_analyze` - Analyze repository
- `repo_codemap` - Generate code map
- `multi_repo_sync` - Sync multiple repos
- `git_audit` - Scan for secrets

### CodeRefactor (5 tools)
- `refactor_symbol` - Rename symbol
- `refactor_impact` - Analyze impact
- `refactor_apply` - Apply refactoring
- `scope_resolution` - Resolve scope
- `search_code` - Search code

### CodeTester (2 tools)
- `qa_run` - Run QA tests
- `qa_status` - Check QA status

### Filesystem (4 tools)
- `fs_tree` - Get file tree
- `fs_read` - Read file
- `fs_write` - Write file
- `fs_glob` - Glob pattern matching

## Development

```bash
# Setup development environment
bash scripts/setup/setup.sh

# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=src/ tests/

# Development mode
uv run python -m src.main
```

## License

MIT