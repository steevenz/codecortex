# CodeCortex for Codex CLI (OpenAI)

Codex CLI supports plugins via the `.codex-plugin/` directory. Format similar to Claude Code.

## Installation

### Plugin auto-load
Plugin is already at `.codex-plugin/plugin.json` — Codex auto-detects when in project root.

### MCP Server
Configure in your Codex CLI MCP settings:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "codex-cli"]
    }
  }
}
```

### Skills
Skills in `.skills/` are auto-loaded by plugin.json (referenced via `"skills": "./.skills/"`).

## Files

```
.codex-plugin/
└── plugin.json              # Plugin manifest (skills)

.skills/                     # Shared skills directory
```

## VS Code + Codex

If using Codex via VS Code, configure MCP in `.vscode/mcp.json`.
