# CodeCortex for Trae & SOLO Trae

Trae IDE (and SOLO/Web version) supports MCP server config + project rules.

## Installation

### MCP Server
Trae reads MCP config from `.trae/mcp.json` or `.trae/mcp_npx.json`:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-codecortex", "run", "python", "-m", "src.main"]
    }
  }
}
```

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
├── mcp.json                  # MCP server config (uv)
├── mcp_npx.json              # Alternate MCP config (npx)
├── system_prompt.md          # CodeCortex usage policy
├── project_rules.md          # CodeCortex rules
├── user_rules.md             # User preferences
└── TRAEBACK_NPX_FIX.md      # NPX troubleshooting
```
