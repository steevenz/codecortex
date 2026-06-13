---
name: agents
description: Mandatory CodeCortex usage policy for AI agents — 6 unified MCP tools
version: 3.0.0
last_updated: 2026-05-26
author: Steeven Andrian
alwaysApply: true
---

# MANDATORY CODECORTEX USAGE POLICY
**ALL AI AGENTS MUST USE CODECORTEX MCP SERVER FOR ALL CODEBASE OPERATIONS**

## 1. CORE MANDATE

### 1.1 Absolute Requirement
**NO exception. NO bypass. NO alternative methods.**

Every AI agent interaction with codebase MUST:
1. Invoke CodeCortex MCP Server first
2. Use CodeCortex tools for analysis
3. Reference CodeCortex output in decisions
4. Verify with CodeCortex post-changes

### 1.2 6 Unified MCP Tools
All domain capabilities accessed via action+args dispatch:

| MCP Tool | Actions | Domain |
|----------|---------|--------|
| `codecortex:repository` | init, inspect, analyze, sync, audit, list, status, remove, branches, diff, commit, log, blame | Repository lifecycle |
| `codecortex:filesystem` | read, write, delete, copy, move, search, tree, info, watch, diff, audit | File operations |
| `codecortex:codebase` | analyze, search, audit, graph, index, symbols, dependencies, metrics | Code intelligence |
| `codecortex:scaffolder` | list_stacks, get_stack, validate_name, list_licenses, generate, make, create | Project scaffolding |
| `codecortex:knowledge` | extract, query, status, relationships | Engineering knowledge |
| `codecortex:idegraph` | search, get, list, ingest, refresh, health, stats, compact, workspace, harvest | Cross-IDE memories |

### 1.3 Prohibited Actions
| Action | Status | Reason |
|--------|--------|--------|
| Direct file read for codebase analysis | ❌ PROHIBITED | Must use CodeCortex |
| Manual code search | ❌ PROHIBITED | Must use CodeCortex |
| Direct code modification | ❌ PROHIBITED | Must analyze with CodeCortex first |
| Architecture review without CodeCortex | ❌ PROHIBITED | Must use CodeCortex tools |

## 2. CODECORTEX TOOL MANDATES

### 2.1 For Code Scanning
```
BEFORE scanning ANY codebase:
→ MUST call codecortex:codebase(action=analyze|search|symbols)
→ MUST call codecortex:repository(action=inspect)
```

### 2.2 For Code Analysis
```
BEFORE analyzing ANY code:
→ MUST call codecortex:codebase(action=analyze|graph|audit|dependencies)
→ MUST call codecortex:knowledge(action=query) for relevant docs
```

### 2.3 For Code Modification
```
BEFORE modifying ANY code:
→ MUST call codecortex:codebase(action=symbols) to locate target
→ MUST call codecortex:codebase(action=dependencies) to find related
→ THEN proceed with modification
→ MUST verify with codecortex:codebase(action=audit) post-change
```

### 2.4 For Project Scaffolding
```
WHEN creating new projects:
→ MUST call codecortex:scaffolder(action=list_stacks) to see available stacks
→ MUST call codecortex:scaffolder(action=validate_name) to check name
→ MUST call codecortex:scaffolder(action=generate|make|create) to scaffold
```

### 2.5 For Cross-IDE Memory
```
WHEN searching past AI interactions:
→ MUST call codecortex:idegraph(action=search|get|list)
→ MUST call codecortex:idegraph(action=ingest) to refresh
→ MUST call codecortex:idegraph(action=compact) to summarize conversations
```

## 3. SYSTEM PROMPT ENFORCEMENT

### 3.1 Detection Patterns
IF ANY of these patterns detected, IMMEDIATELY invoke CodeCortex:

| Trigger Word | MCP Tool + Action |
|--------------|-------------------|
| "find code" | codecortex:codebase(action=search) |
| "search" | codecortex:codebase(action=search) or codecortex:idegraph(action=search) |
| "analyze" | codecortex:codebase(action=analyze) |
| "refactor" | codecortex:codebase(action=dependencies) |
| "memory" / "history" | codecortex:idegraph(action=search) |
| "ingest" | codecortex:idegraph(action=ingest) |
| "scaffold" | codecortex:scaffolder(action=generate) |
| "knowledge" | codecortex:knowledge(action=query) |

## 4. VERIFICATION STEPS

### 4.1 Pre-Operation Verification
```
[ ] CodeCortex MCP Server is available
[ ] Database connection is established via CODECORTEX_DB_PATH
[ ] SideCortex tables exist in shared database/codecortex.db
```

### 4.2 Post-Operation Verification
```
[ ] Changes verified with codecortex:codebase(action=audit)
[ ] No breaking changes detected
[ ] Maker tests pass: pytest tests/test_maker.py -q
```

## 5. ARCHITECTURE OVERVIEW

### 5.1 Database
- **Single database**: `database/codecortex.db` (SQLite WAL)
- All modules share via `DatabaseManager` (singleton)
- SideCortex tables (conversations, messages, workspaces, ides, etc.) co-located
- Graph backends: Kuzu/Neo4j/FalkorDB for relationship graphs

### 5.2 Module Structure
```
src/
├── main.py                    # CortexOrchestrator + 6 tool registration
├── core/                      # Shared: api_response, insight, database, logging
├── api/                       # Unified API tools (4 tools)
├── modules/
│   ├── coderepository/        # Repository operations
│   ├── codeindex/             # AST indexing
│   ├── codegraph/             # Graph + golden knowledge
│   ├── filesystem/            # File system operations
│   ├── coderefactor/          # Refactoring engine
│   ├── codetester/            # QA testing
│   ├── knowledgegraph/        # Engineering knowledge extraction
│   └── idegraph/              # Cross-IDE memory harvesting
├── scripts/                   # CLI, HTTP server
```

### 5.3 Standards
- **Python 3.12** | **UV** package manager | **Pytest** with coverage
- **DDD + Hexagonal Architecture** per module
- **Tree-Sitter 0.25.x** for parsing
- **Docblocks**: `@project CodeCortex`, `@author Steeven Andrian`, `@copyright (c) 2026 CODDY Codework`
- **Class naming**: No `Service`/`Repository` suffix when folder already declares role (coding-standard R1)

## 6. COMPLIANCE AUDIT

### 6.1 Self-Assessment Questions
BEFORE each response:
- [ ] Have I invoked CodeCortex for this request?
- [ ] Are my findings based on CodeCortex output?
- [ ] Am I using the correct unified tool (repository|filesystem|codebase|scaffolder|knowledge|idegraph)?
- [ ] Will my response pass the verification checklist?

### 6.2 Violation Consequences
- First violation: Warning + re-process with CodeCortex
- Second violation: Decline request with policy reference
- Third violation: Escalate to system administrator

## 7. CONTACT & SUPPORT

For CodeCortex issues:
- Verify database: `CODECORTEX_DB_PATH` → default `database/codecortex.db`
- Run tests: `pytest tests/test_maker.py -q`
- Full syntax check: `python scripts/validate_state.py`

---
**Signature**: CodeCortex Policy Engine v3.0
**Effective**: 2026-05-26
**Compliance**: 100% MANDATORY
