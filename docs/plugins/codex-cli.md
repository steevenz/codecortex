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
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-codecortex", "run", "python", "-m", "src.main"]
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
