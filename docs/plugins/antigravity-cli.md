# CodeCortex for Antigravity CLI / IDE / Agent

Antigravity CLI, Antigravity IDE, and Antigravity Agent all share the same `.antigravity/` config format.

## Installation

### 1. MCP Server
Add to Antigravity CLI config:

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

### 2. Copy config directory
```bash
cp -r .antigravity /path/to/your/project/
```

### 3. Reference in Antigravity config
In your Antigravity CLI config, add:
```yaml
imports:
  - .antigravity/config.yaml
```

## Files

```
.antigravity/
├── mcp.json        # MCP server config
├── config.yaml     # CodeCortex agent config
└── rules.yaml      # CodeCortex rules
```
