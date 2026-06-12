# CodeCortex for Zed Editor

Zed editor supports MCP servers and custom settings via `.zed/settings.json`.

## Installation

### 1. Add MCP server to `.zed/settings.json`

```json
{
  "mcp_servers": [
    {
      "name": "codecortex",
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-codecortex", "run", "python", "-m", "src.main"]
    }
  ]
}
```

### 2. Add assistant instructions (`.zed/assistant/instructions.md`)

Create `.zed/assistant/instructions.md`:

```markdown
# CodeCortex Usage

ALL codebase operations MUST use CodeCortex MCP tools:
- codecortex:codebase — analyze, search, audit, graph, test, refactor
- codecortex:repository — init, inspect, analyze, sync
- codecortex:knowledge — query engineering knowledge
- codecortex:idegraph — cross-IDE memory search

Workflow: Search → Graph → Impact → Modify → Audit → Test
```

## Files

```
.zed/
├── settings.json              # MCP server config + editor settings
└── assistant/
    └── instructions.md        # AI assistant custom instructions
```
