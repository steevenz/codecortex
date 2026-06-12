# CodeCortex for OpenClaude

OpenClaude is an open-source Claude Code alternative with native Claude Code plugin compatibility.

## Installation

OpenClaude supports the same `plugin.json` format as Claude Code:

```bash
cp -r .claude-plugin /path/to/your/project/
```

### MCP Server
Configure in OpenClaude's MCP settings:

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
OpenClaude supports the same `.skills/` directory as Claude Code. Skills auto-discover via plugin.json.

## Files

```
├── .claude-plugin/plugin.json     # Same plugin.json format as Claude Code
├── .skills/                       # Shared skills (auto-discovery)
└── docs/plugins/openclaude.md     # This guide
```
