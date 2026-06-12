# CodeCortex Mandatory Rules

## Core Rule
ALL codebase operations MUST use CodeCortex MCP Server. No exceptions.

## Pre-Modification Checklist
- [ ] Search symbol locations with `codecortex:codebase(action=search)`
- [ ] Build dependency graph with `codecortex:codebase(action=graph, args={sub_action:"build"})`
- [ ] Find callers/dependents with `codecortex:codebase(action=graph, args={sub_action:"query", query_type:"callers"})`
- [ ] Assess impact with `codecortex:codebase(action=refactor, args={sub_action:"impact"})`

## Post-Modification Checklist
- [ ] Audit changes with `codecortex:codebase(action=audit)`
- [ ] Run tests with `codecortex:codebase(action=test, args={sub_action:"run"})`
