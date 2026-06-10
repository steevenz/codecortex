# Fix for MCP Connection Error

## Problem
```
2026-05-23T18:09:52.857+08:00 [error] [mcp.config.usrlocalmcp.codecortex] MCPClient#startFailed Connection closed
```

## Solution

### Use UV Command (Recommended)
```json
{
  "mcpServers": {
    "codecortex": {
      "command": "uv",
      "args": [
        "--directory",
        "~\\MCP\\mcp-codecortex",
        "run",
        "python",
        "-m",
        "src.main"
      ],
      "env": {
        "CODECORTEX_DB_PATH": "${HOME}/.codecortex/db.sqlite",
        "CODECORTEX_GRAPH_BACKEND": "none",
        "CODECORTEX_MAX_REPOS": "50"
      }
    }
  }
}
```

### Why This Works
1. **UV** is the project's package manager (lockfile: uv.lock)
2. **Python -m src.main** runs the MCP server directly
3. **Graph backend: none** avoids dependency issues

### Environment Variables
| Variable | Value | Purpose |
|----------|-------|---------|
| `CODECORTEX_TRANSPORT` | `stdio` | MCP stdio transport |
| `CODECORTEX_GRAPH_BACKEND` | `none` | In-memory graph (no install) |
| `CODECORTEX_MAX_REPOS` | `50` | Repository quota |

### Test Command
```bash
cd ~\MCP\mcp-codecortex
uv run python -m src.main
```

Expected: Server starts and waits for MCP connections.