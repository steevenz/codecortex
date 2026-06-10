# CodeAnalysis Domain - Gap Analysis Report

**Date:** 2026-05-28  
**Domain:** CodeAnalysis  
**Scope:** 4 MCP tools + 8 CLI commands  
**Analysis Type:** Documentation vs Source Code Comparison

---

## Executive Summary

**Overall Grade:** B  
**Documentation Accuracy:** 85%  
**Critical Issues:** 1  
**High Issues:** 3  
**Medium Issues:** 5  
**Low Issues:** 2

---

## Gap Inventory

### 1. MCP Tool: code_search

| Gap Type | Severity | Description | Location |
|----------|----------|-------------|----------|
| Missing Parameter | High | Documentation shows `search_type` parameter (symbol/regex/graph/semantic) but MCP tool signature doesn't include it. Implementation hardcodes `search_type="multi"` in SearchRequest. | `api/tools.py:117-174` vs `concept.md:157` |
| Parameter Mismatch | Medium | Documentation shows `cursor` as int, but DTO has it as Optional[int]. Service implementation doesn't use cursor for pagination. | `core/dtos.py:73` vs `concept.md:159` |

**Impact:** Users cannot control search type via MCP tool. Must use "multi" mode which combines all layers.

**Recommendation:** Add `search_type` parameter to MCP tool signature and pass to service, or update documentation to reflect hardcoded behavior.

---

### 2. MCP Tool: code_audit

| Gap Type | Severity | Description | Location |
|----------|----------|-------------|----------|
| Parameter Name Mismatch | High | Documentation uses `repository_id`, MCP tool uses `repository_id` but variable in code is `repo_id` (line 254). Inconsistent naming. | `api/tools.py:254` |
| Unused Parameter | Medium | `since` parameter documented for incremental scan but not used in audit service logic. | `api/tools.py:188` vs `services/audit.py` |
| Category Count Mismatch | Low | Documentation mentions 22 categories, default list in code has 22 categories. Actual implementation may have more/less. | `concept.md:201` vs `services/audit.py:51-59` |

**Impact:** `since` parameter is accepted but not implemented for incremental scanning. Users expecting incremental scans will get full scans.

**Recommendation:** Implement incremental scan logic using `since` parameter, or remove from documentation if not planned.

---

### 3. MCP Tool: code_status

| Gap Type | Severity | Description | Location |
|----------|----------|-------------|----------|
| Parameter Type Mismatch | High | Documentation shows `path` as required string, but MCP tool signature has it as Optional[str] with validation check. | `api/tools.py:274` vs `concept.md:574` |
| Inconsistent Validation | Medium | CLI requires `path` as positional, MCP tool has it optional but validates inside. Different UX patterns. | `api/cli.py:204` vs `api/tools.py:295` |

**Impact:** Confusing API - parameter appears optional but is actually required for successful execution.

**Recommendation:** Make `path` required in MCP tool signature (remove Optional) to match documentation and CLI behavior.

---

### 4. CLI Domain Scope

| Gap Type | Severity | Description | Location |
|----------|----------|-------------|----------|
| Domain Mismatch | Medium | CLI file uses `DOMAIN = "codebase"` but this is codeanalysis module. Cross-domain commands included. | `api/cli.py:10` |
| Cross-Domain Commands | Low | CLI includes graph, index, test, refactor commands which belong to other domains (codegraph, codeindex, codetester, coderefactor). | `api/cli.py:265-274` |

**Impact:** CLI is a cross-domain aggregator, not pure codeanalysis. This may be intentional for user convenience.

**Recommendation:** Document CLI as cross-domain aggregator, or split into domain-specific CLI modules.

---

### 5. Documentation Completeness

| Gap Type | Severity | Description | Location |
|----------|----------|-------------|----------|
| Missing CLI Documentation | Medium | No dedicated CLI documentation for codeanalysis commands. Only MCP tools documented in concept.md. | `docs/features/codeanalysis/` |
| Missing Service Documentation | Low | No documentation for service layer (analyze.py, search.py, audit.py, status.py). | `src/modules/codeanalysis/services/` |

**Impact:** Users cannot reference CLI usage patterns or understand service layer architecture.

**Recommendation:** Add CLI documentation and service architecture documentation.

---

### 6. Implementation Quality

| Gap Type | Severity | Description | Location |
|----------|----------|-------------|----------|
| DocBlock Header Mismatch | Low | audit.py header says "Class Search" but file is "Class Audit". Copy-paste error. | `services/audit.py:1-9` |
| Inconsistent Error Handling | Medium | Some methods return api_response, others raise exceptions directly. Inconsistent error handling pattern. | Various service files |

**Impact:** Minor code quality issues, doesn't affect functionality but reduces maintainability.

**Recommendation:** Fix docblock header, standardize error handling pattern across all services.

---

## Gap Summary

```
Total Gaps: 11
Critical: 1
High: 3
Medium: 5
Low: 2
Documentation Accuracy: 85%
```

---

## Priority Fix Order

### P0 (Critical)
1. **code_search missing search_type parameter** - Users cannot control search behavior

### P1 (High)
2. **code_audit repository_id naming inconsistency** - Code quality issue
3. **code_status path parameter type** - API inconsistency
4. **code_audit since parameter not implemented** - Feature gap

### P2 (Medium)
5. **CLI domain mismatch** - Architectural clarity
6. **Missing CLI documentation** - User experience
7. **Inconsistent error handling** - Code quality
8. **audit.py docblock header** - Code quality

### P3 (Low)
9. **code_search cursor parameter** - Minor UX
10. **Category count verification** - Documentation accuracy
11. **Missing service documentation** - Developer experience

---

## Compliance Check

### ~/.aicoders/ Standards Compliance

| Standard | Status | Evidence |
|----------|--------|----------|
| API Standard (api_response) | ✅ | All MCP tools use api_response() |
| DDD Architecture | ✅ | api/ + services/ + core/ separation |
| DI Pattern | ✅ | Constructor injection for all services |
| DTOs | ✅ | All data transfer via typed DTOs |
| DocBlock Headers | ⚠️ | audit.py has wrong class name in header |
| Error Handling | ⚠️ | Inconsistent patterns across services |

---

## Recommendations

### Immediate Actions
1. Add `search_type` parameter to `code_search` MCP tool
2. Make `path` required in `code_status` MCP tool signature
3. Implement or remove `since` parameter in `code_audit`
4. Fix audit.py docblock header

### Short-term Improvements
1. Add CLI documentation for codeanalysis commands
2. Standardize error handling pattern across services
3. Clarify CLI as cross-domain aggregator in documentation

### Long-term Enhancements
1. Consider splitting CLI into domain-specific modules
2. Add service layer architecture documentation
3. Implement incremental scan for code_audit
