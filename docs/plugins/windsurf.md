# CodeCortex for Windsurf

## Prerequisites
- [Windsurf](https://codeium.com/windsurf) IDE installed
- CodeCortex MCP server running

## Installation

### 1. MCP Server
Add to Windsurf MCP config:

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

### 2. Copy config
```bash
cp -r .windsurf /path/to/your/project/
```

### 3. Rules auto-load
Windsurf reads `.windsurf/rules/` automatically. No additional config needed.

## Usage

CodeCortex MCP tools are available via Windsurf's MCP integration.

## Files

```
.windsurf/
├── mcp.json            # MCP server config
└── rules/
    └── codecortex.md    # CodeCortex rules
```
