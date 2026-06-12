# CodeCortex for Verdent AI

Verdent AI is an agentic coding suite with parallel agents, plan mode, BYOK, and Eco Mode. Supports VS Code and JetBrains.

## Installation

### VS Code Extension
Install CodeCortex as an MCP server in Verdent AI settings:

1. Open Verdent AI Settings
2. Go to MCP Servers → Add Server
3. Configure:

```json
{
  "name": "codecortex",
  "command": "uv",
  "args": ["--directory", "/path/to/mcp-codecortex", "run", "python", "-m", "src.main"]
}
```

### Project Config (`.verdent/`)

Create `.verdent/agents/codecortex.yaml`:

```yaml
name: codecortex
description: Code intelligence via MCP
tools:
  - codecortex:codebase
  - codecortex:repository
  - codecortex:knowledge
  - codecortex:idegraph
rules:
  - Always use CodeCortex MCP tools for codebase operations
  - Run graph build before architecture queries
  - Analyze impact before modifications
```

## Files

```
.verdent/
├── agents/
│   └── codecortex.yaml    # CodeCortex agent for Verdent
└── rules.md               # CodeCortex rules
```
