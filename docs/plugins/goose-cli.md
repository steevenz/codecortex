# CodeCortex for Goose CLI

## Prerequisites
- [Goose CLI](https://github.com/block/goose) installed
- CodeCortex MCP server running

## Installation

### 1. MCP Server
Add to Goose CLI config:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "goose-cli"]
    }
  }
}
```

### 2. Copy config
```bash
cp -r .goose /path/to/your/project/
```

### 3. Reference in Goose config
In your Goose CLI configuration, add:
```yaml
extensions:
  - from: .goose/config.yaml
```

## Files

```
.goose/
├── mcp.json       # MCP server config
└── config.yaml    # Goose extension config
```
