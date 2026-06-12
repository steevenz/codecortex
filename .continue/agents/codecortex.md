---
name: CodeCortex
description: Code intelligence via MCP — codebase analysis, graph queries, refactoring, architecture audit, cross-IDE memory, and project scaffolding
---

# CodeCortex Agent

Use CodeCortex MCP tools for ALL codebase operations.

## Tools
- `codecortex:codebase` — analyze, search, audit, graph, status, index, test, refactor
- `codecortex:repository` — init, inspect, analyze, sync, audit, git
- `codecortex:knowledge` — extract, query, status, relationships
- `codecortex:idegraph` — search, ingest, refresh, compact, harvest
- `codecortex:scaffolder` — list_stacks, validate_name, generate, create

## Workflow
1. Search: `action=search, args={query:"<target>", semantic:true}`
2. Analyze: `action=analyze, args={target:"<file>"}`
3. Graph: `action=graph, args={sub_action:"build"}`
4. Impact: `action=refactor, args={sub_action:"impact"}`
5. Modify → Audit → Test
