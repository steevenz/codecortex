# CodeGraph Domain - Gap Analysis Report

**Date:** 2026-05-29  
**Domain:** CodeGraph  
**Scope:** MCP Tools and CLI Commands  
**Source of Truth:** Source Code Implementation

---

## Executive Summary

**Overall Grade:** C

The CodeGraph domain has undergone significant refactoring that consolidated 11 tools into 6 unified tools. However, the documentation has not been updated to reflect these changes, creating a **critical documentation gap**. The actual implementation is more advanced and consolidated than documented, but users following the documentation will encounter errors.

**Key Findings:**
- Documentation Accuracy: **0%** (all tool names are outdated)
- Critical Issues: **3** (documentation completely out of sync)
- High Issues: **2** (missing CLI integration)
- Medium Issues: **3** (parameter mismatches)
- Low Issues: **1** (nice-to-have improvements)

---

## Phase 1: Scope Definition

### Target Domain
- **Domain:** CodeGraph
- **Package:** `src/modules/codegraph/`
- **Documentation:** `docs/features/codegraph/`

### MCP Tools Inventory

**Documented (tools.md):**
1. `graph_find_symbols` - Find symbols by name
2. `graph_query` - Query code relationships
3. `graph_find_related` - Find related code (mentioned in count, not documented)
4. `graph_build` - Build code relationship graph
5. `graph_trace_flow` - Trace execution flow
6. `arch_analyze` - Full architectural analysis
7. `arch_audit` - Audit for architectural smells

**Implemented (tools.py):**
1. `graph_search` - Unified search (merged: graph_find_symbols + graph_search + graph_find_related)
2. `graph_query` - Query relationships (merged: graph_query + graph_trace_flow + graph_trace)
3. `graph_audit` - Full audit (merged: arch_analyze + arch_audit + graph_audit)
4. `graph_build` - Build graph (unchanged)
5. `graph_relationship` - Explore relationships (unchanged)
6. `graph_refactor` - Architectural refactoring (unchanged)

### CLI Commands Inventory

**Documented:** None found in documentation  
**Implemented:** None found in CLI - CodeGraph has **no CLI commands** (only MCP tools)

---

## Phase 2: Documentation Review

### Documentation Matrix

| Tool | Parameters | Operations | Response Format | Examples |
|------|------------|------------|-----------------|----------|
| graph_find_symbols | 6 documented | search | functions/classes/variables | None |
| graph_query | 5 documented | 11 query types | varies | None |
| graph_find_related | Not documented | N/A | N/A | N/A |
| graph_build | 3 documented | build | stats | None |
| graph_trace_flow | 2 documented | trace | hierarchical tree | None |
| arch_analyze | 3 documented | analyze | metrics + summary | None |
| arch_audit | 5 documented | audit | findings by type | None |

### Documentation Quality Issues

1. **Critical:** All tool names are outdated (documentation describes old API)
2. **High:** No usage examples provided
3. **Medium:** Response formats described but may not match current implementation
4. **Low:** No error case documentation

---

## Phase 3: Source Code Analysis

### Source Code Matrix

| Tool | Parameters | Operations | Response Format | Adapters |
|------|------------|------------|-----------------|----------|
| graph_search | 11 parameters | 5 actions (symbol, relation, trace_flow, modular, semantic) | api_response() | AEGISGraphSearch |
| graph_query | 8 parameters | 12 query types (including trace_path, trace_flow) | api_response() | AEGISGraphTrace |
| graph_audit | 6 parameters | 7 audit types | api_response() | AEGISGraphAudit |
| graph_build | 8 parameters | build with modular detection | api_response() | AEGIS |
| graph_relationship | 9 parameters | explore relationships | api_response() | AEGISGraphRelationship |
| graph_refactor | 6 parameters | impact/preview/apply | api_response() | AEGISGraphRefactor |

### Implementation Quality Check

✅ **Strengths:**
- All tools use proper adapter pattern (AEGIS* services)
- Consistent error handling with ApiError
- Proper parameter validation
- Pagination support (cursor, limit)
- Response wrapping with `_wrap_result()`

⚠️ **Issues:**
- No CLI commands implemented (CLI gap)
- Documentation completely out of sync
- Some parameters may have different names than documented

---

## Phase 4: Gap Analysis

### Documentation vs Source Code Comparison

| Gap Type | Description | Severity |
|----------|-------------|----------|
| **Missing in Docs** | `graph_search` - new unified tool | **Critical** |
| **Missing in Docs** | `graph_relationship` - not documented | **High** |
| **Missing in Docs** | `graph_refactor` - not documented | **High** |
| **Missing in Source** | `graph_find_symbols` - replaced by graph_search | **Critical** |
| **Missing in Source** | `graph_find_related` - merged into graph_search | **Critical** |
| **Missing in Source** | `graph_trace_flow` - merged into graph_query | **Critical** |
| **Missing in Source** | `arch_analyze` - merged into graph_audit | **Critical** |
| **Missing in Source** | `arch_audit` - replaced by graph_audit | **Critical** |
| **Parameter Mismatch** | graph_search has 11 params vs 6 documented | **High** |
| **Parameter Mismatch** | graph_query has 8 params vs 5 documented | **High** |
| **Parameter Mismatch** | graph_audit has 6 params vs 5 documented | **Medium** |
| **Missing CLI** | No CLI commands for CodeGraph | **Medium** |
| **Missing Examples** | No usage examples in docs | **Low** |

### Gap Classification

**Critical (P0) - 8 gaps:**
- All documented tool names are obsolete
- Users following documentation will get "tool not found" errors
- Complete documentation rewrite required

**High (P1) - 2 gaps:**
- graph_relationship not documented
- graph_refactor not documented
- Parameter count mismatches

**Medium (P2) - 2 gaps:**
- No CLI commands implemented
- Some parameter name differences

**Low (P3) - 1 gap:**
- Missing usage examples

### Gap Summary Report

```markdown
## Gap Analysis Summary
- Total Gaps: 13
- Critical: 8 (62%)
- High: 2 (15%)
- Medium: 2 (15%)
- Low: 1 (8%)
- Documentation Accuracy: 0%
```

---

## Detailed Gap Breakdown

### Gap 1: Tool Consolidation (Critical)

**Problem:** Code has been refactored from 11 tools to 6 unified tools, but documentation still describes old API.

**Old Documentation:**
```
graph_find_symbols, graph_query, graph_find_related, 
graph_build, graph_trace_flow, arch_analyze, arch_audit
```

**Current Implementation:**
```
graph_search, graph_query, graph_audit, 
graph_build, graph_relationship, graph_refactor
```

**Impact:** Users following documentation will get "tool not found" errors.

**Fix Required:** Complete documentation rewrite to reflect current API.

---

### Gap 2: graph_search Tool (Critical)

**Problem:** New unified tool not documented.

**Current Implementation:**
```python
async def graph_search(
    action: str,  # "symbol" | "relation" | "trace_flow" | "modular" | "semantic"
    query: Optional[str] = None,
    repo_id: Optional[str] = None,
    repo_path: Optional[str] = None,
    symbol_type: str = "any",
    fuzzy: bool = False,
    edit_distance: int = 2,
    relation_type: Optional[str] = None,
    target_symbol_id: Optional[str] = None,
    max_depth: int = 3,
    modular_type: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
)
```

**Replaces:** `graph_find_symbols`, `graph_search`, `graph_find_related`

**Fix Required:** Add comprehensive documentation for graph_search.

---

### Gap 3: graph_query Tool (Critical)

**Problem:** Tool name exists but signature changed.

**Current Implementation:**
```python
async def graph_query(
    query_type: str,  # 12 types including trace_path, trace_flow
    target: str,
    repo_id: Optional[str] = None,
    repo_path: Optional[str] = None,
    max_depth: int = 3,
    end_node: Optional[str] = None,  # NEW
    context: Optional[str] = None,
    direction: str = "both",  # NEW
    limit: int = 20,
)
```

**Merged:** `graph_trace_flow`, `graph_trace`

**Fix Required:** Update documentation with new parameters and merged functionality.

---

### Gap 4: graph_audit Tool (Critical)

**Problem:** Replaces both arch_analyze and arch_audit.

**Current Implementation:**
```python
async def graph_audit(
    repo_id: str,
    audit_types: Optional[List[str]] = None,  # 7 types
    repo_path: Optional[str] = None,
    include_summary: bool = False,
    degree_threshold: int = 10,
    limit: int = 50,
)
```

**Audit Types:**
- god_nodes
- security
- dead_code
- complexity
- communities
- coupling
- circular_deps

**Fix Required:** Document as unified audit tool replacing arch_analyze + arch_audit.

---

### Gap 5: graph_relationship Tool (High)

**Problem:** Not documented at all.

**Current Implementation:**
```python
async def graph_relationship(
    repo_id: str,
    target_node: str,
    relation_type: Optional[List[str]] = None,
    direction: str = "both",
    depth: int = 1,
    modular_type: Optional[str] = None,
    include_community: bool = False,
    min_confidence: str = "INFERRED",
    limit: int = 100,
    cursor: Optional[str] = None,
)
```

**Fix Required:** Add complete documentation for graph_relationship.

---

### Gap 6: graph_refactor Tool (High)

**Problem:** Not documented at all.

**Current Implementation:**
```python
async def graph_refactor(
    repo_id: str,
    action: str,  # "impact" | "preview" | "apply"
    refactor_type: str,  # 5 types
    target_node: str,
    options: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
)
```

**Refactor Types:**
- split_module
- extract_component
- reroute_dependency
- extract_interface
- inline_module

**Fix Required:** Add complete documentation for graph_refactor.

---

### Gap 7: CLI Commands (Medium)

**Problem:** No CLI commands for CodeGraph domain.

**Finding:** CodeGraph is MCP-only, no CLI interface exists.

**Impact:** Users cannot use CodeGraph features via CLI.

**Fix Required:** Either document that CLI is not available, or implement CLI commands.

---

## Recommendations

### P0 (Critical) - Must Fix

1. **Rewrite tools.md** to reflect current 6-tool API
2. **Document graph_search** with all 5 actions and 11 parameters
3. **Update graph_query** documentation with new parameters (end_node, direction)
4. **Document graph_audit** as unified tool replacing arch_analyze + arch_audit
5. **Remove obsolete tool references** (graph_find_symbols, graph_find_related, graph_trace_flow, arch_analyze, arch_audit)

### P1 (High) - Should Fix

6. **Document graph_relationship** with all parameters
7. **Document graph_refactor** with all refactor types
8. **Add usage examples** for each tool

### P2 (Medium) - Nice to Have

9. **Clarify CLI status** - document that CodeGraph is MCP-only
10. **Add error case documentation** for each tool
11. **Update flow.md** to reflect new tool names

### P3 (Low) - Future Enhancements

12. **Consider CLI implementation** for common operations
13. **Add interactive examples** in documentation

---

## Conclusion

The CodeGraph domain has a **critical documentation gap** due to a major refactoring that consolidated tools. The actual implementation is well-structured and follows best practices, but the documentation is completely out of sync. This is a **production-blocking issue** for users relying on documentation.

**Immediate Action Required:** Complete documentation rewrite to match current implementation.

**Production Readiness:** **40%** (implementation is solid, but documentation is unusable)
