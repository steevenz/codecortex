# CodeCortex Rules for Windsurf

**ALL codebase operations MUST use CodeCortex MCP Server.**

## MCP Tools
- `codecortex:repository` — repo init, inspect, analyze, sync, audit
- `codecortex:codebase` — analyze, search, audit, graph, test, refactor
- `codecortex:filesystem` — read, write, delete, search
- `codecortex:scaffolder` — generate, create projects
- `codecortex:knowledge` — query engineering knowledge
- `codecortex:idegraph` — search cross-IDE memories

## Pre-Modification
1. Search symbols: `codecortex:codebase(action=search, args={query:"<target>"})`
2. Build graph: `codecortex:codebase(action=graph, args={sub_action:"build"})`
3. Find dependents: `codecortex:codebase(action=graph, args={sub_action:"query", query_type:"callers"})`
4. Impact analysis: `codecortex:codebase(action=refactor, args={sub_action:"impact"})`

## Post-Modification
- Audit: `codecortex:codebase(action=audit)`
- Test: `codecortex:codebase(action=test, args={sub_action:"run"})`
