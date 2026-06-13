# CodeCortex for Trae & SOLO Trae

Trae IDE (and SOLO/Web version) supports MCP server config + project rules.

## Installation

### MCP Server

Trae reads MCP config from `.trae/mcp.json`:

> **IMPORTANT**: All IDE configs must point to **Node.js** (`index.cjs`), not Python. See [Setup Guide](../guides/how-to-setup-mcp.md).

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": [
        "C:/Users/steevenz/MCP/mcp-codecortex/scripts/server/js/index.cjs",
        "--ide",
        "trae"
      ]
    }
  }
}
```

Replace the path with your actual CodeCortex installation path.

### System Prompt & Rules
Trae auto-loads files from `.trae/`:
- `.trae/system_prompt.md` — Mandatory CodeCortex usage policy
- `.trae/project_rules.md` — CodeCortex project rules
- `.trae/user_rules.md` — User preferences

### SOLO Trae
For SOLO Trae (web-based), the configuration format is **the same** — copy `.trae/` to project root.

## Files

```
.trae/
├── mcp.json                  # MCP server config (node)
├── mcp_npx.json              # Alternate MCP config (npx)
├── system_prompt.md          # CodeCortex usage policy
├── project_rules.md          # CodeCortex rules
├── user_rules.md             # User preferences
└── TRAEBACK_NPX_FIX.md      # NPX troubleshooting
```
