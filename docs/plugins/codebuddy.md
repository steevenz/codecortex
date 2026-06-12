# CodeCortex for Codebuddy

Codebuddy is an AI code editor. Add CodeCortex via MCP server configuration.

## Installation

### MCP Server
Configure in Codebuddy's MCP settings:

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

### Custom Instructions
Add to Codebuddy's custom instructions/system prompt:

```
ALL codebase operations MUST use CodeCortex MCP Server.
Tools: codecortex:codebase, codecortex:repository, codecortex:knowledge, codecortex:idegraph
Workflow: Search → Graph → Impact → Modify → Audit → Test
```
