# CodeCortex Rules for Gemini CLI

## Mandatory
- Always use CodeCortex MCP tools for codebase operations
- Never read files directly for analysis — use codecortex:codebase
- Run `codecortex:codebase(action=graph, args={sub_action:"build"})` before queries

## Pre-Modification
1. `codecortex:codebase(action=search, args={query:"<target>"})` — locate symbols
2. `codecortex:codebase(action=graph, args={sub_action:"query", query_type:"callers", target:"<symbol>"})` — find dependents
3. `codecortex:codebase(action=refactor, args={sub_action:"impact", target:"<symbol>"})` — assess blast radius

## Post-Modification
- `codecortex:codebase(action=audit)` — verify no regressions
- `codecortex:codebase(action=test, args={sub_action:"run"})` — run tests
