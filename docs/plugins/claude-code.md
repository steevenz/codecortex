# CodeCortex for Claude Code

Claude Code supports plugins natively via the `.claude-plugin/` directory.

## Installation

### Plugin auto-load
Plugin is already at `.claude-plugin/plugin.json` — Claude Code auto-detects when in project root.

### MCP Server
Add to `claude_desktop_config.json` or project-level MCP config:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "claude-code"]
    }
  }
}
```

### Skills
Skills in `.skills/` are auto-loaded by plugin.json. Claude Code also supports hooks via `hooks/`:

```bash
# Session-start hook auto-loads SOUL.md
hooks/
├── hooks.json
└── session-start
```

## Files

```
.claude-plugin/
└── plugin.json              # Plugin manifest (skills + hooks)

.skills/
├── codecortex-codebase/     # Code intelligence
├── codecortex-idegraph/     # IDE memory
├── codecortex-knowledge/    # Knowledge graph
├── codecortex-project/      # Scaffolding
└── codecortex-refactor/     # Refactoring

.hooks/
├── hooks.json
└── session-start

SOUL.md                      # Hook entry point
```
