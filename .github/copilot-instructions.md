# CodeCortex — GitHub Copilot Custom Instructions

## Mandatory: Use CodeCortex MCP Server for codebase operations

### MCP Server Setup (in your editor's MCP config)
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

### Available Tools
- `codecortex:codebase` — analyze, search, audit, graph, test, refactor
- `codecortex:repository` — init, inspect, analyze, sync
- `codecortex:filesystem` — read, write, delete, search
- `codecortex:knowledge` — query engineering knowledge
- `codecortex:idegraph` — cross-IDE memory search
- `codecortex:scaffolder` — project scaffolding

### Workflow
1. Search → locate symbols
2. Graph → build dependencies
3. Impact → analyze changes
4. Modify
5. Audit → verify
6. Test → run tests
