# CodeCortex Documentation

This directory contains all project documentation following the Aegis Codeworks project-structure-standard.

## Documentation Structure

### 📋 **drafts/** - Work in Progress
- `archives/` - Deprecated documents kept for reference (currently empty; historical docs removed after merge)
- `concepts/` - Draft architectural concepts and ideas

### 🎯 **product/** - Product Management Artifacts
- `prd/` - Approved Product Requirements Documents
- `roadmap.md` - Timeline and milestones
- `success-metrics.md` - OKRs, KPIs, and success criteria

### 🏗️ **architecture/** - System Architecture Documentation
- `architecture.md` - Core architectural design and domain map
- `security.md` - Security guards, SSRF prevention, path validation
- `api/` - Global API documentation
  - `specs.md` - OpenAPI/Swagger contracts
  - `endpoints.md` - MCP tool endpoints reference
  - `codebase.md` - Code structure documentation
- `concepts/` - Core philosophies and Architecture Decision Records (ADRs)

### 🚀 **features/** - Feature-Based Documentation
Each feature gets its own subfolder containing:
- `concept.md` - Business concept and why this feature exists
- `flow.md` - Execution pipeline and data flow
- `tools.md` - MCP tool reference with parameters
- `output.md` - Data shape, schema, and example output
- `llm-impact.md` - How the feature enriches LLM code understanding
- `examples/` - Sample JSON payloads and response data
- `sub-features/` - Recursive sub-feature documentation

### 📚 **guides/** - Setup and Operations Guides
Installation, deployment, configuration, and operational procedures.

### � **workflows/** - Agentic Workflow Playbooks
Structured workflows for AI agents: CCT reasoning, bug hunting, refactoring, security audits, and multi-repo operations.

### � **versions/** - Versioned Documentation Snapshots
- `CHANGELOG.md` - Version history and recent changes
- `v[MAJOR].[MINOR]/` - Documentation for each version
  - `implementation-plans/` - Implementation plans
  - `tasks/` - Tasks from implementation plans
  - `changelogs/` - Change logs
  - `analysis/` - Analysis per version
  - `walkthroughs/` - Summary reports

### 📖 **glossary.md** - Domain & Technical Terms
Definitions of domain-specific terminology and technical concepts used throughout the project.

### 🏠 **index.md** - Executive Summary
High-level overview of the CodeCortex project, its purpose, and key components.

## Documentation Standards

All documentation must:
1. Use **lowercase-dashed** filenames
2. Follow the Aegis Codeworks documentation standards
3. Include proper docblocks and copyright headers
4. Be written in clear, professional English
5. Use Markdown format with proper structure
6. Align with the 6-domain architecture (CodeRepository, CodeIndex, CodeGraph, Filesystem, CodeRefactor, CodeTester)

## Quick Links

- **features/index.md** - Feature map with documentation by domain (6 domains + Core)
- **features/support-matrix.md** - Languages, frameworks, MCP, LLMs, OS, databases, backends, QA tools
- **features/codeindex/concept.md** - Code indexing docs (TreeSitter, semantic search, etc.)
- **features/codegraph/concept.md** - Code graph & architecture analysis docs
- **features/coderepository/concept.md** - Repository management docs
- **features/filesystem/concept.md** - File operations docs
- **features/coderefactor/concept.md** - Code refactoring docs
- **features/codetester/concept.md** - QA automation docs
- **features/core/concept.md** - Core infrastructure docs (database, token economy, CLI)
- **architecture/architecture.md** - Domain map, DI wiring, pipeline flow, backend abstraction
- **architecture/security.md** - SSRF guards, path validation, label sanitization reference
- **guides/how-to-setup-mcp.md** - MCP server setup and configuration
- **guides/how-to-use-cli.md** - CLI usage guide
- **workflows/workflow-index.md** - Master index of all agentic workflows
- **versions/changelog.md** - Version history and recent changes
- **index.md** - Executive summary and project overview
- **../README.md** - Project root README with quick start guide

---

*This document follows Aegis Codeworks documentation standards.*
