# CodeCortex for Continue.dev

Continue.dev supports MCP servers and custom agents via the `.continue/` directory.

## Installation

### 1. MCP Server
Add to your Continue config (`config.json` or YAML):

```json
{
  "experimental": {
    "mcpServers": {
      "codecortex": {
        "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "continue"]
      }
    }
  }
}
```

### 2. Add CodeCortex agent (`.continue/agents/codecortex.md`)

```markdown
---
name: CodeCortex
description: Code intelligence via MCP — codebase analysis, graph queries, refactoring, architecture audit
---

# CodeCortex Agent

Use CodeCortex MCP tools for all codebase operations:
- codecortex:codebase — analyze, search, audit, graph, test, refactor
- codecortex:repository — init, inspect, analyze, sync
- codecortex:knowledge — query engineering knowledge
- codecortex:idegraph — cross-IDE memory search

## Workflow
1. Search: codecortex:codebase(action=search, args={query:"<target>"})
2. Analyze: codecortex:codebase(action=analyze, args={target:"<file>"})
3. Impact: codecortex:codebase(action=refactor, args={sub_action:"impact"})
4. Modify → Audit → Test
```

### 3. Add rules (`.continue/rules/codecortex.md`)

```markdown
ALL codebase operations MUST use CodeCortex MCP Server.
- Run graph build before architecture queries
- Analyze impact before modifications
- Verify with audit post-change
```

## Files

```
.continue/
├── config.json              # MCP server config
├── agents/
│   └── codecortex.md        # CodeCortex agent definition
└── rules/
    └── codecortex.md        # CodeCortex rules
```
