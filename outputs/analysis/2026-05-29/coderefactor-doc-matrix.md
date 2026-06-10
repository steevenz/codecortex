# CodeRefactor Documentation Matrix

**Date:** 2026-05-29
**Source:** concept.md, README.md
**Scope:** MCP tool `code_refactor` (12 actions)

---

## Documented Features (from concept.md)

### Tool: code_refactor

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repo_id | string | Yes | - | Repository UUID |
| action | string | Yes | - | Refactoring operation (12 actions) |
| target_symbol | string | Yes | - | Target in "file_path:line" or "module::name" format |
| changes | dict | No | None | Action-specific change details |
| dry_run | boolean | No | True | Preview without applying |
| ai_feedback | boolean | No | False | Include AI suggestions |
| confidence_threshold | int | No | 85 | Minimum confidence to auto-apply |

**Actions (12 total):**
| Action | Tier | Read-only | Changes Required |
|--------|------|-----------|------------------|
| impact | Symbol | Yes | None |
| rename | Symbol | No | {"new_name": "..."} |
| move | Symbol | No | {"target_file": "..."} |
| change_signature | Symbol | No | {"add_params": [...], "remove_params": [...]} |
| extract_function | Symbol | No | {"new_name": "...", "start_line": X, "end_line": Y} |
| inline_function | Symbol | No | {} |
| preview | Workflow | Yes | {"preview_action": "..."} |
| apply | Workflow | No | {"apply_action": "..."} |
| rename_file | VCS | No | {"new_path": "..."} |
| rename_folder | VCS | No | {"new_name": "..."} |
| move_file | VCS | No | {"target_dir": "..."} |
| modularize | VCS | No | {"target_domain": "...", "strategy": "auto"} |

**Response Format:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "...",
  "data": {
    "status": "success|error",
    "message": "...",
    "repository_id": "...",
    "action": "...",
    "changes": [...],
    "blast_radius": {...},
    "commit_hash": "...",
    "validation_result": "..."
  }
}
```

**Examples:** Not provided in concept.md (only flow descriptions)

---

## Documentation Quality Issues

### 1. README.md Outdated
- **Issue:** README.md mentions "6 tools" but actual implementation has 1 unified tool
- **Impact:** Medium (P2) - Confusing for users
- **Action Required:** Update README.md to match actual architecture

### 2. Missing Examples
- **Issue:** concept.md has no concrete usage examples
- **Impact:** Medium (P2) - Harder for users to understand tool usage
- **Action Required:** Add 3-5 usage examples per action

### 3. Missing CLI Documentation
- **Issue:** No CLI commands documented (none exist)
- **Impact:** Low (P3) - CLI not required per workflow
- **Action Required:** Consider adding CLI if needed for testing

---

## Documentation Accuracy Score: 75%

**Strengths:**
- Comprehensive concept.md with detailed architecture
- All 12 actions documented
- Clear parameter documentation
- Detailed flow descriptions

**Weaknesses:**
- README.md outdated (6 tools vs 1 unified tool)
- No concrete usage examples
- No error case documentation
