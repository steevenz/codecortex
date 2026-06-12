# CodeCortex Usage Policy for Gemini CLI

**ALL codebase operations MUST use CodeCortex MCP Server. No exceptions.**

## MCP Tools Available

| Tool | Actions |
|------|---------|
| `codecortex:repository` | init, inspect, analyze, sync, audit, git |
| `codecortex:filesystem` | read, write, delete, copy, move, search, watch |
| `codecortex:codebase` | analyze, search, audit, graph, status, index, test, refactor |
| `codecortex:scaffolder` | list_stacks, validate_name, generate, create |
| `codecortex:knowledge` | extract, query, status, relationships |
| `codecortex:idegraph` | search, ingest, refresh, compact, harvest |

## Workflow

1. **Search**: `codecortex:codebase(action=search, args={query, semantic:true})`
2. **Analyze**: `codecortex:codebase(action=analyze, args={target})`
3. **Graph**: `codecortex:codebase(action=graph, args={sub_action:"build"})`
4. **Audit**: `codecortex:codebase(action=audit, args={target:"."})`
5. **Refactor**: `codecortex:codebase(action=refactor, args={sub_action:"impact"})`
