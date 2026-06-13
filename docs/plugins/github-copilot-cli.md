# CodeCortex for GitHub Copilot CLI

## Prerequisites
- [GitHub Copilot CLI](https://github.com/github/gh-copilot) installed
- CodeCortex MCP server accessible

## Installation

### 1. Copy custom instructions
```bash
cp .github/copilot-instructions.md /path/to/your/project/.github/
```

### 2. MCP Server
GitHub Copilot does not natively support MCP. But if using Copilot via **VS Code** or **JetBrains**, configure MCP:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "github-copilot-cli"]
    }
  }
}
```

- **VS Code**: Add to `.vscode/mcp.json`
- **JetBrains**: Add to `.idea/mcp.json` or Settings → Tools → MCP Server
- **CLI**: Reference system prompt manually in queries

## Files

```
.github/
└── copilot-instructions.md    # CodeCortex instructions for Copilot
```
