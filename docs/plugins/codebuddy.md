# CodeCortex for Codebuddy

Codebuddy is an AI code editor. Add CodeCortex via MCP server configuration.

## Installation

### MCP Server
Configure in Codebuddy's MCP settings:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "codebuddy"]
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
