---
description: Safe Refactoring Pipeline — impact analysis, preview, and apply with blast radius awareness
title: WFK_RFC_001 — Safe Refactoring Pipeline
workflow_id: WFK_RFC_001
version: 2.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
codification: CODDY-Architecture-v1.0 §5
---

# WFK_RFC_001: Safe Refactoring Pipeline

> **Goal**: Refactor code safely with mandatory impact analysis, dry-run preview, and user confirmation.
> **Trigger**: User asks to refactor, rename, move, extract, inline, or change signatures.
> **Time**: Seconds (impact) to minutes (apply with validation).
> **Cost**: Low-to-medium (impact is read-only; apply is the only write operation).
> **Safety Rule**: **Never apply without impact analysis + preview + user confirmation.**

---

## 1. Trigger Phrases

- *"Refactor this"*
- *"Rename this function"*
- *"Move this class"*
- *"Extract this logic"*
- *"Inline this method"*
- *"Change the signature"*
- *"Move this file"*
- *"Modularize this monolith"*
- *"Split this god class"*
- *"Safe rename across codebase"*

---

## 2. The Golden Rule

```
impact  →  preview  →  apply
(read)    (dry)      (write)
   │          │          │
   ▼          ▼          ▼
 NEVER    ALWAYS    ONLY WITH
 SKIP     DRY_RUN   USER CONFIRM
```

**If any step returns an error or high-risk blast radius, STOP and ask the user.**

---

## 3. Pipeline Overview

```
Step 1: Impact Analysis (cb:refactor:impact) ───┐
Step 2: Preview          (cb:refactor:*, dry_run) ───┤───► Deliverable
Step 3: Apply            (cb:refactor:*, dry_run=false) ───┘ (user confirms)
```

---

## 4. Step 1 — Impact Analysis (Mandatory, Read-Only)

**Purpose**: Determine blast radius — how many files and symbols will be affected.

### MCP Call
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "impact",
    target_symbol: "src/service.py::process_order",
    changes: {
      new_name: "process_order_v2"
    }
  }
```

### Response Fields
```json
{
  "impact": {
    "affected_files": ["src/service.py", "src/controller.py", "tests/test_service.py"],
    "affected_symbols": ["process_order", "OrderController.handle_request", "TestService.test_order"],
    "risk": "low"
  },
  "plan": {
    "steps": ["Rename in src/service.py", "Update call in src/controller.py", "Update test assertion"],
    "estimated_effort": "2 minutes"
  }
}
```

### Risk Assessment
| Risk | Files Affected | AI Action |
|------|---------------|----------|
| `low` | `<= 3` | Proceed to Step 2 |
| `medium` | `4-10` | Warn user, proceed to Step 2 |
| `high` | `> 10` | **STOP**. Ask user: "This affects <N> files. Are you sure?" |

### Supported Refactor Types for Impact
| Type | target_symbol Format | Changes Field |
|------|---------------------|---------------|
| `rename` | `file.py::SymbolName` | `new_name` |
| `move` | `file.py::SymbolName` | `target_file` |
| `change_signature` | `file.py::funcName` | `params_add`, `params_remove` |
| `extract_function` | `file.py::` (with line range) | `new_name`, `line_start`, `line_end` |
| `inline_function` | `file.py::funcName` | (none, removes function) |
| `rename_file` | `src/old.py` | `new_path` |
| `move_file` | `src/old.py` | `new_path` |
| `modularize` | `src/monolith.py` | `target_domain` |

### CLI
```bash
codecortex ref impact --repo-id <id> src/service.py::process_order
```

---

## 5. Step 2 — Preview (Dry Run)

**Purpose**: Show exactly what will change without modifying any files.

### 5.1 Rename Preview
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "rename",
    target_symbol: "src/service.py::process_order",
    changes: { new_name: "process_order_v2" },
    dry_run: true
  }
```

### 5.2 Move Preview
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "move",
    target_symbol: "src/service.py::OrderService",
    changes: { target_file: "src/domain/order/service.py" },
    dry_run: true
  }
```

### 5.3 Extract Function Preview
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "extract",
    target_symbol: "src/service.py::",
    changes: {
      new_name: "validate_order",
      line_start: 42,
      line_end: 55,
      target_file: "src/service.py"
    },
    dry_run: true
  }
```

### 5.4 Change Signature Preview
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "signature",
    target_symbol: "src/service.py::create_user",
    changes: {
      params_add: [{ name: "role", type: "str", default: "user" }],
      params_remove: ["deprecated_param"]
    },
    dry_run: true
  }
```

### 5.5 Modularize Preview
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "modularize",
    target_symbol: "src/monolith.py",
    changes: { target_domain: "src/domain/" },
    dry_run: true
  }
```

### Preview Response Fields
```json
{
  "status": "preview",
  "message": "Would rename 5 occurrences across 3 files",
  "changes": [
    {
      "file": "src/service.py",
      "line": 10,
      "old": "process_order",
      "new": "process_order_v2",
      "status": "pending"
    },
    {
      "file": "src/controller.py",
      "line": 25,
      "old": "process_order",
      "new": "process_order_v2",
      "status": "pending"
    }
  ],
  "blast_radius": {
    "files_affected": 3,
    "symbols_affected": 5,
    "risk": "low"
  },
  "validation_result": {
    "passed": true,
    "warnings": []
  }
}
```

### AI Must Check Before Proceeding
| Check | Condition | Action |
|-------|-----------|--------|
| `validation_result.passed` | Must be `true` | If `false`, STOP and report conflicts |
| `validation_result.warnings` | Should be empty | If present, surface to user |
| `blast_radius.risk` | Should be `low` or `medium` | If `high`, ask for confirmation |
| `changes[]` | Review each change | Ensure no unexpected modifications |

### CLI
```bash
codecortex ref rename --repo-id <id> src/service.py::process_order --new-name process_order_v2
codecortex ref move --repo-id <id> src/service.py::OrderService --target-file src/domain/order/service.py
codecortex ref extract --repo-id <id> src/service.py --line-start 42 --line-end 55 --new-name validate_order
codecortex ref modularize --repo-id <id> src/monolith.py --target-domain src/domain/
```

---

## 6. Step 3 — Apply (User Confirmation Required)

**Purpose**: Execute the refactoring. Only after user explicitly confirms.

### User Confirmation Pattern
```
AI: "Preview shows 3 files will change:
     1. src/service.py: rename process_order → process_order_v2
     2. src/controller.py: update call site
     3. tests/test_service.py: update test assertion
     Risk: low. Apply? (yes/no)"

User: "yes"
```

### Apply Call
```
MCP: codecortex:codebase
  action: "refactor"
  repo_id: "<repo_id>"
  args: {
    sub_action: "rename",
    target_symbol: "src/service.py::process_order",
    changes: { new_name: "process_order_v2" },
    dry_run: false
  }
```

### Apply Response Fields
```json
{
  "status": "ok",
  "message": "Renamed 5 occurrences across 3 files",
  "changes": [
    { "file": "src/service.py", "line": 10, "old": "process_order", "new": "process_order_v2", "status": "applied" }
  ],
  "blast_radius": { "files_affected": 3, "symbols_affected": 5, "risk": "low" },
  "commit_hash": "abc123def",
  "validation_result": { "passed": true, "warnings": [] }
}
```

### Post-Apply Actions
1. **Sync Index**: `repo:sync` to refresh the graph after changes.
2. **Run Tests**: `cb:test:run` to verify nothing broke.
3. **Report**: Confirm to user which files changed.

### CLI Apply
```bash
codecortex ref rename --repo-id <id> src/service.py::process_order --new-name process_order_v2 --apply
codecortex repo sync /path/to/project --reindex-updated
codecortex qa run --target . --filter "*test_service*"
```

---

## 7. Refactoring Type Reference

### 7.1 Symbol Rename
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "rename",
    target_symbol: "file.py::OldName",
    changes: { new_name: "NewName" }
  }
```

### 7.2 Move Symbol
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "move",
    target_symbol: "old_file.py::Symbol",
    changes: { target_file: "new_file.py" }
  }
```

### 7.3 Extract Function
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "extract",
    target_symbol: "file.py::",
    changes: { new_name: "newFunc", line_start: 10, line_end: 25 }
  }
```

### 7.4 Inline Function
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "inline",
    target_symbol: "file.py::funcToInline"
  }
```

### 7.5 Change Signature
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "signature",
    target_symbol: "file.py::funcName",
    changes: {
      params_add: [{ name: "newParam", type: "str" }],
      params_remove: ["oldParam"]
    }
  }
```

### 7.6 Rename File
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "rename_file",
    target_symbol: "src/old.py",
    changes: { new_path: "src/new.py" }
  }
```

### 7.7 Move File
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "move_file",
    target_symbol: "src/old.py",
    changes: { new_path: "src/domain/new.py" }
  }
```

### 7.8 Modularize (Split Monolith)
```
MCP: codecortex:codebase
  action: "refactor"
  args: {
    sub_action: "modularize",
    target_symbol: "src/monolith.py",
    changes: { target_domain: "src/domain/" }
  }
```

---

## 8. Undo Support

CodeCortex supports undo for refactoring operations.

### List Undoable Operations
```bash
codecortex cg refactor <repo_id> undo_list
```

### Undo Last Operation
```bash
codecortex cg refactor <repo_id> undo
```

---

## 9. Deliverable Format

```markdown
# Safe Refactoring Report

## 1. Impact Analysis
- **Target**: `src/service.py::process_order`
- **Type**: rename
- **Files Affected**: 3
- **Symbols Affected**: 5
- **Risk**: low

## 2. Preview (Dry Run)
| File | Line | Old | New | Status |
|------|------|-----|-----|--------|
| src/service.py | 10 | process_order | process_order_v2 | pending |
| src/controller.py | 25 | process_order | process_order_v2 | pending |
| tests/test_service.py | 42 | process_order | process_order_v2 | pending |

## 3. Validation
- **Passed**: true
- **Warnings**: none

## 4. User Confirmation
- **Status**: Approved

## 5. Apply Result
- **Status**: ok
- **Commit**: abc123def
- **Files Modified**: 3
- **Tests Post-Apply**: passed (5/5)

## 6. Post-Refactor Checklist
- [x] Index synced
- [x] Tests pass
- [x] No new warnings
```

---

## 10. Anti-Patterns to Avoid

| Anti-Pattern | Why It's Dangerous | Correct Approach |
|-------------|-------------------|----------------|
| Skip impact analysis | Don't know blast radius | Always run `cb:refactor:impact` first |
| Skip dry_run preview | Unexpected changes applied | Always preview before apply |
| Apply without user confirmation | AI should not write production code autonomously | Get explicit "yes" |
| Ignore `validation_result.passed=false` | Conflicts will break build | Fix conflicts, re-preview |
| Not syncing index after apply | Stale graph misleads future analysis | Run `repo:sync` |
| Not running tests after apply | Silent regressions | Run `cb:test:run` |

---

## 11. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `dry_run: true` preview before apply | ~100% on mistakes | Prevents costly reverts |
| `changes` object with minimal scope | ~30% | Narrow impact analysis |
| Skip `cb:test:run` if tests don't cover affected symbol | ~25% | Check coverage first |
| `limit: 10` on blast radius results | ~40% | Cap affected files list |

### Parallel Execution
- No parallel execution during refactor (sequential by design: impact → preview → apply)
- But `impact` analysis can be parallelized with `cb:status` check for repo health
- Post-apply `cb:test:run` and `repo:sync` can run in parallel

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| `impact.risk == "high"` AND `affected_files > 20` | STOP. Ask user before preview. |
| `impact.affected_files == 0` | Symbol not found. Stop and inform user. |
| `preview.validation_result.passed == false` | Don't apply. Show conflicts to user. |
| User cancels after preview | Stop. No sync needed. |

### Cache Reuse
- If impact analysis ran in last 5 minutes → reuse (code hasn't changed)
- If tests passed in last run → only run tests for affected files
- Always sync index after apply — stale graph = misleading future impact analysis

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [analysis-orchestra-workflow.md](analysis-orchestra-workflow.md)*
