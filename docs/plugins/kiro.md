# CodeCortex for Kiro IDE

Kiro IDE supports plugins via `.kiro/` directory with agents, skills, hooks, and MCP.

## Installation

### 1. Copy CodeCortex to your Kiro config
```bash
cp -r .kiro/codecortex /path/to/your/project/.kiro/
```

### 2. MCP Server
Add to your Kiro MCP config (`.kiro/mcp.json` or MCP settings):

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

### 3. Link skills
Kiro reads from `.kiro/skills/`. Symlink or copy CodeCortex skills:

```bash
ln -s ../../.skills/codecortex-codebase .kiro/skills/
ln -s ../../.skills/codecortex-knowledge .kiro/skills/
```

## Files

```
.kiro/
├── codecortex/
│   ├── agent.md         # CodeCortex agent for Kiro
│   └── hooks.json       # Pre/post hooks
├── mcp.json             # MCP server config
└── skills/ → .skills/   # Symlinked skills
```
