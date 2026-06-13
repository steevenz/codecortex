# CodeCortex for Antigravity CLI / IDE / Agent

Antigravity CLI, Antigravity IDE, and Antigravity Agent all share the same `.antigravity/` config format.

## Installation

### 1. MCP Server
Add to Antigravity CLI config:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "antigravity-cli"]
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
