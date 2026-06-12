---
name: CodeCortex
description: Code intelligence via MCP — codebase analysis, graph queries, refactoring, architecture audit, cross-IDE memory
---

# CodeCortex Agent for Kiro IDE

## MCP Tools
- `codecortex:codebase` — analyze, search, audit, graph, status, index, test, refactor
- `codecortex:repository` — init, inspect, analyze, sync, audit, git
- `codecortex:filesystem` — read, write, delete, copy, move, search, watch
- `codecortex:knowledge` — extract, query, status, relationships
- `codecortex:idegraph` — search, ingest, refresh, compact, harvest

## Workflow
1. Search symbols → `codecortex:codebase(action=search, args={query:"<target>"})`
2. Build graph → `codecortex:codebase(action=graph, args={sub_action:"build"})`
3. Analyze impact → `codecortex:codebase(action=refactor, args={sub_action:"impact"})`
4. Modify code
5. Audit → `codecortex:codebase(action=audit)`
6. Test → `codecortex:codebase(action=test, args={sub_action:"run"})`
