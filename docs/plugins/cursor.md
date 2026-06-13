# CodeCortex for Cursor

Cursor IDE supports plugins via the `.cursor-plugin/` directory + MCP server integration.

## Installation

### Plugin auto-load
Plugin is already at `.cursor-plugin/plugin.json` — Cursor auto-detects.

### MCP Server
**Via Cursor Settings UI:**
1. `Cursor Settings → MCP → Add New MCP Server`
2. Fill:
   - **Name**: `codecortex`
   - **Type**: `command`
   - **Command**: `node scripts/server/js/index.cjs --ide cursor`

**Or via `.cursor/mcp.json`:**
```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "cursor"]
    }
  }
}
```

### Hooks
Cursor supports hooks. Configured in `.cursor-plugin/plugin.json`:
```json
{
  "hooks": "./hooks/hooks-cursor.json"
}
```

## Files

```
.cursor-plugin/
└── plugin.json              # Plugin manifest

.cursor/
└── mcp.json                 # (optional) MCP server config

.skills/                     # Shared skills directory
```
