# CodeCortex Usage Instructions

ALL codebase operations MUST use CodeCortex MCP Server.

## MCP Tools Available
- `codecortex:codebase` — analyze, search, audit, graph, status, index, test, refactor
- `codecortex:repository` — init, inspect, analyze, sync, audit, git
- `codecortex:knowledge` — extract, query, status, relationships
- `codecortex:idegraph` — search, ingest, refresh, compact, harvest
- `codecortex:filesystem` — read, write, delete, search, watch
- `codecortex:scaffolder` — list_stacks, validate_name, generate, create

## Workflow
1. Search → Locate symbols: `action=search, args={query:"<target>"}`
2. Analyze → Deep dive: `action=analyze, args={target:"<file>"}`
3. Graph → Build: `action=graph, args={sub_action:"build"}`
4. Impact → Assess: `action=refactor, args={sub_action:"impact"}`
5. Modify code
6. Audit → Verify: `action=audit`
7. Test → Run: `action=test, args={sub_action:"run"}`
