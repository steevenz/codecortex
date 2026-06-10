---
Version: 3.0.0
Date: 2026-05-26
---

# Working Context — CodeCortex MCP Server

## Current Truth
- **Active Task**: idegraph module standardization & .agents/ alignment
- **Project Root**: `~\MCP\mcp-codecortex`
- **Python**: 3.12 | **Package Manager**: UV | **MCP**: FastMCP (stdio)
- **Database**: `database/codecortex.db` (SQLite WAL — single shared DB for ALL modules)
- **6 Unified MCP Tools**: repository, filesystem, codebase, scaffolder, knowledge, idegraph

## Core Status
- idegraph module integrated: package paths fixed, api/tools.py created, shared DB
- 13 SideCortex tables co-located in codecortex.db (sync_runs, ides, workspaces, conversations, messages, etc.)
- 11 insight generators registered for idegraph actions
- All 17 maker tests pass consistently
- **QA Testing Harness Complete**: 15/15 workflows validated natively through MCP and CLI interfaces without failures.

## Context Gap
- docs/features/scaffolder/ needs to be added to docs/features/README.md
- IdeGraph unit tests are missing (`tests/unit/idegraph`)

## Done List
- [x] idegraph module: package paths fixed (src. → src.modules.idegraph.)
- [x] idegraph module: api/tools.py with unified tool (10 actions)
- [x] idegraph module: insight generators (11 total)
- [x] idegraph module: class naming per coding-standard R1
- [x] idegraph module: docblocks standardized
- [x] idegraph module: registered in main.py (6th tool)
- [x] idegraph module: shared database/codecortex.db (no separate DB)
- [x] .agents/agents.md: updated with 6 unified tools
- [x] .agents/state.yaml → states/current.yaml
- [x] scaffolder module: complete documentation structure created following codeanalysis standard
- [x] scaffolder module: concept.md with all required sections
- [x] scaffolder module: 7 sub-feature docs created (scaffold_list_stacks, scaffold_get_stack, scaffold_validate_name, scaffold_list_licenses, scaffold_generate, scaffold_make, scaffold_create)
- [x] scaffolder module: 6 JSON examples created (list_stacks.json, get_stack.json, validate_name.json, generate_content.json, generate_class.json, create_project.json)
- [x] scaffolder module: ai-impact-token-efficiency.md analysis completed
- [x] scaffolder module: comprehensive AI impact deep analysis with 20+ usage scenarios (create new code, init project, restructure, boilerplate, stack discovery)
- [x] scaffolder module: 100% compliance with ~/.aicoders/rules standards
- [x] scaffolder module: added .aicoders/ and .agents/ to STANDARD_ROOT_DIRECTORIES
- [x] scaffolder module: implemented _write_ai_context_files() for AI context generation
- [x] scaffolder module: implemented _write_project_docs() for project documentation generation
- [x] scaffolder module: greenfield project generation now fully compliant with ~/.aicoders/rules
- [x] scaffolder module: added 6 documentation types to Decision Matrix (doc_draft, doc_planning, doc_concept, doc_feature, doc_subfeature, doc_ai_impact)
- [x] scaffolder module: implemented _build_document_body() for documentation generation per ~/.aicoders/docs/standards/documentation.md
- [x] scaffolder module: scaffold_make now supports 34 types (28 code + 6 documentation)
- [x] scaffolder module: updated scaffold_make docstring to document new documentation types
- [x] scaffolder module: tested documentation file generation (all 6 types working)
- [x] scaffolder module: updated concept.md to reflect 34 types (28 code + 6 documentation)
- [x] scaffolder module: updated ai-impact-token-efficiency.md to include documentation types
- [x] Context Hygiene: `.agents/persona.yaml` created
- [x] Context Hygiene: `.agents/routing-table.yaml` created
- [x] Context Hygiene: `contexts/project.md` merged into `principal.md` and deleted
- [x] Context Hygiene: legacy `SOUL.md` removed
- [x] Context Hygiene: `idegraph` subcommand added to `scripts/cli.py` and `src/cli/__init__.py`
- [x] QA Harness: Validated all 15 native MCP workflows (Discovery, Bug Hunting, Security, Refactoring, Architecture, Greenfield, Brownfield, CCT Deep Reasoning, etc.)
- [x] QA Harness: Fixed `repositories.vcs_type` NOT NULL database constraints.
- [x] QA Harness: Fixed `ApiError` leak returning 500 across generic CLI handler.
- [x] QA Harness: Fixed Pytest deadlock on Windows via `asyncio_mode="auto"`.

## Target Queue
1. [ ] Write unit tests for idegraph services (`tests/unit/idegraph/`)
2. [x] Update `docs/features/README.md` to link `scaffolder` and `idegraph` documentation.
