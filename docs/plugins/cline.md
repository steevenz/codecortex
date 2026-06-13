# CodeCortex for Cline

## Prerequisites
- [Cline](https://github.com/cline/cline) VS Code extension installed
- CodeCortex MCP server running

## Installation

### 1. MCP Server
Add to Cline MCP config (`cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "cline"]
    }
  }
}
```

### 2. Copy config
```bash
cp -r .cline /path/to/your/project/
```

### 3. Reference .clinerules
Cline reads `.clinerules` from the project root automatically. Make sure `.cline/.clinerules` is visible to Cline.

## Usage

Cline loads CodeCortex MCP tools automatically. Use in prompts:
- "Analyze this codebase with CodeCortex"
- "Find callers of X using codecortex:codebase"

## Files

```
.cline/
├── mcp.json       # MCP server config
└── .clinerules    # CodeCortex rules for Cline
```
