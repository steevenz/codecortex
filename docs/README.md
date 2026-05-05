# CodeCortex Documentation

This directory contains all project documentation following the Aegis Codeworks project-structure-standard.

## Documentation Structure

### 📋 **drafts/** - Work in Progress
- `archives/` - Deprecated documents kept for reference
- `concepts/` - Draft architectural concepts and ideas
- `prd/` - Draft Product Requirements Documents
- `technical-specs/` - Draft technical specifications

### 🎯 **product/** - Product Management Artifacts
- `prd/` - Approved Product Requirements Documents
- `roadmap.md` - Timeline and milestones
- `success-metrics.md` - OKRs, KPIs, and success criteria

### 🏗️ **architecture/** - System Architecture Documentation
- `ARCHITECTURE.md` - Core architectural design and domain map
- `SECURITY.md` - Security guards, SSRF prevention, path validation
- `api/` - Global API documentation
  - `specs.md` - OpenAPI/Swagger contracts
  - `endpoints.md` - MCP tool endpoints reference
  - `codebase.md` - Code structure documentation
- `concepts/` - Core philosophies and Architecture Decision Records (ADRs)

### 🚀 **features/** - Feature-Based Documentation
Each feature gets its own subfolder containing:
- `concept.md` - Business concept and why this feature exists
- `technical-spec.md` - Detailed technical requirements
- `technical-design.md` - Diagrams and class structures
- `ui-ux.md` - User flows and wireframes

### 📚 **guides/** - Setup and Operations Guides
Installation, deployment, configuration, and operational procedures.

### 📌 **versions/** - Versioned Documentation Snapshots
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

- **architecture/ARCHITECTURE.md** - Domain map, DI wiring, pipeline flow, backend abstraction
- **architecture/SECURITY.md** - SSRF guards, path validation, label sanitization reference
- **versions/CHANGELOG.md** - Version history and recent changes
- **index.md** - Executive summary and project overview
- **../README.md** - Project root README with quick start guide

---

*This document follows Aegis Codeworks documentation standards.*
