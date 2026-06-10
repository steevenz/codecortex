# Scaffolder Domain - Gap Analysis Report

**Date:** 2026-05-29  
**Domain:** Scaffolder  
**Scope:** 7 MCP tools + CLI commands  
**Analysis Method:** Documentation vs Source Code Comparison  
**Source of Truth:** Source code implementation

---

## Executive Summary

**Overall Documentation Accuracy:** 0% (No dedicated documentation exists)

**Critical Finding:** The scaffolder domain has **NO dedicated documentation** in `docs/features/scaffolder/`. Only brief mentions exist in:
- `docs/features/README.md` (line 22 - single line mention)
- `docs/guidelines/how-to-use-cli.md` (partial CLI reference)
- `docs/MCP_TOOLS_INSIGHT.md` (partial tool reference)

**Gap Severity:** CRITICAL (P0) - Complete absence of domain documentation

---

## Gap Analysis Summary

| Gap Type | Count | Severity |
|----------|-------|----------|
| Missing Documentation Directory | 1 | Critical |
| Missing concept.md | 1 | Critical |
| Missing sub-features/ | 7 | High |
| Missing examples/ | 7 | High |
| Missing ai-impact-token-efficiency.md | 1 | High |
| **Total Gaps** | **17** | **Critical** |

---

## Detailed Gap Analysis

### 1. Missing Documentation Directory (CRITICAL)

**Location Expected:** `docs/features/scaffolder/`  
**Actual State:** Does not exist  
**Impact:** No discoverable documentation for scaffolder domain  
**Severity:** Critical (P0)

**Required Structure (per codeanalysis standard):**
```
docs/features/scaffolder/
├── concept.md                          # Main domain doc
├── ai-impact-token-efficiency.md       # Token efficiency analysis
├── sub-features/                       # Individual tool docs
│   ├── scaffold_list_stacks/
│   │   └── concept.md
│   ├── scaffold_get_stack/
│   │   └── concept.md
│   ├── scaffold_validate_name/
│   │   └── concept.md
│   ├── scaffold_list_licenses/
│   │   └── concept.md
│   ├── scaffold_generate/
│   │   └── concept.md
│   ├── scaffold_make/
│   │   └── concept.md
│   └── scaffold_create/
│       └── concept.md
└── examples/                           # Usage examples
    ├── list_stacks.json
    ├── get_stack.json
    ├── validate_name.json
    ├── generate_content.json
    ├── generate_class.json
    └── create_project.json
```

---

### 2. Missing concept.md (CRITICAL)

**Required Sections (per codeanalysis standard):**
1. Domain header (version, AI impact, production readiness)
2. Business context
3. Why it exists
4. Theoretical foundation
5. Architecture diagram
6. Domain boundary
7. CLI architecture note
8. ~/.aicoders/ compliance
9. Error codes table
10. 10/10 AI Coder Impact features
11. Related sub-features links

**Current State:** Does not exist  
**Severity:** Critical (P0)

---

### 3. Missing Sub-Feature Documentation (HIGH)

**Missing sub-feature docs for 7 MCP tools:**

| Tool | Missing Doc | Severity |
|------|------------|----------|
| scaffold_list_stacks | sub-features/scaffold_list_stacks/concept.md | High |
| scaffold_get_stack | sub-features/scaffold_get_stack/concept.md | High |
| scaffold_validate_name | sub-features/scaffold_validate_name/concept.md | High |
| scaffold_list_licenses | sub-features/scaffold_list_licenses/concept.md | High |
| scaffold_generate | sub-features/scaffold_generate/concept.md | High |
| scaffold_make | sub-features/scaffold_make/concept.md | High |
| scaffold_create | sub-features/scaffold_create/concept.md | High |

**Each sub-feature doc should include:**
- Purpose section
- Why it exists section
- Parameters table
- Output format
- Algorithm description
- Use case

---

### 4. Missing Examples Documentation (HIGH)

**Missing example files for 7 MCP tools:**
- list_stacks.json
- get_stack.json
- validate_name.json
- generate_content.json
- generate_class.json
- create_project.json

**Each example should include:**
- JSON request example
- JSON response example
- Common use case example
- Error case example

---

### 5. Missing AI Impact Token Efficiency Analysis (HIGH)

**Location Expected:** `docs/features/scaffolder/ai-impact-token-efficiency.md`  
**Current State:** Does not exist  
**Severity:** High (P1)

**Required Analysis:**
- Token efficiency metrics for each tool
- Scenario-based analysis (5 typical AI coder scenarios)
- Token savings calculation
- Overall token efficiency assessment

---

## Source Code Inventory

### MCP Tools (7 tools in api/tools.py)

1. **scaffold_list_stacks** - List available technology stacks
2. **scaffold_get_stack** - Get detailed info for one stack
3. **scaffold_validate_name** - Validate and normalize project name
4. **scaffold_list_licenses** - List available license types
5. **scaffold_generate** - Generate single content file (preview)
6. **scaffold_make** - Generate class file per Decision Matrix (28 types)
7. **scaffold_create** - Full project scaffolding (dry_run=True default)

### CLI Commands (7 commands in api/cli.py)

1. **sc_list_stacks** - List stacks
2. **sc_get_stack** - Get stack details
3. **sc_validate_name** - Validate name
4. **sc_list_licenses** - List licenses
5. **sc_generate** - Generate content
6. **sc_make** - Generate class
7. **sc_create** - Create project

### Core Components

- **adapters/**: stack.py, template.py, filesystem.py, git.py
- **core/**: config.py, constants.py, dtos.py, exceptions.py, generators.py, interfaces.py, license.py, maker.py, name.py
- **services/**: scaffold.py, cli.py

### DTOs (core/dtos.py)

- ProjectType
- FileConventions
- Stack
- Project
- Template

---

## Recommendations

### P0 (Critical - Blocker)
1. **Create docs/features/scaffolder/ directory structure**
2. **Create concept.md with all required sections**
3. **Document all 7 MCP tools with parameters and examples**

### P1 (High - Important)
4. **Create sub-features/ directory with individual tool docs**
5. **Create examples/ directory with JSON examples**
6. **Create ai-impact-token-efficiency.md analysis**

### P2 (Medium - Enhancement)
7. **Add CLI command documentation**
8. **Add architecture diagrams**
9. **Add integration guides**

---

## Production Readiness Assessment

**Current Production Readiness:** 0% (Documentation Blocker)

**Blockers:**
- No discoverable documentation
- No concept.md explaining domain purpose
- No sub-feature documentation
- No examples for AI coders
- No AI impact analysis

**Path to 100% Production Readiness:**
1. Create complete documentation structure (P0)
2. Write concept.md following codeanalysis standard (P0)
3. Document all 7 tools with parameters and examples (P0)
4. Create sub-feature docs (P1)
5. Create examples (P1)
6. Create AI impact token efficiency analysis (P1)
7. Test all tools via CLI and MCP (P2)
8. Validate documentation accuracy (P2)

---

## Conclusion

The scaffolder domain is **functionally complete** but **documentationally absent**. The source code implementation is production-ready with 7 MCP tools and CLI commands, but there is **zero documentation** following the codeanalysis standard. This is a **critical blocker** for AI coder discoverability and adoption.

**Immediate Action Required:** Create complete documentation structure following codeanalysis standard.
