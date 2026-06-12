---
name: codecortex-refactor
description: Use when renaming symbols, moving code, extracting/inlining functions, changing signatures, modularizing monoliths, or performing any safe semantic refactoring with mandatory impact analysis and validation via CodeCortex
---

# codecortex:codebase → refactor — Safe Semantic Refactoring (WFK_RFC_001)

**7 sub_actions**: `impact | rename | move | extract | inline | signature | modularize`

**Tool**: `codecortex:codebase` with `action: refactor`

**Docs**: `docs/workflows/safe-refactoring-workflow.md` | `docs/features/coderefactor/concept.md`

---

## The Golden Rule

```
impact  →  preview  →  apply
(read)    (dry)      (write)
   │          │          │
   ▼          ▼          ▼
 NEVER    ALWAYS    ONLY WITH
 SKIP     DRY_RUN   USER CONFIRM
```

**If any step errors or risk is `high`, STOP and ask the user.**

---

## Step 1 — Impact Analysis (Mandatory, Read-Only)

**Purpose**: Determine blast radius — files and symbols affected.

```
action: refactor
args: {
  sub_action: "impact",
  target_symbol: "src/service.py::process_order",
  changes: {new_name: "process_order_v2"},
  dry_run: true
}
```

| Risk | Files | Action |
|------|-------|--------|
| `low` | ≤ 3 | Proceed |
| `medium` | 4-10 | Warn user |
| `high` | > 10 | STOP, ask user |

**If `affected_files == 0`**: Symbol not found. Stop.

---

## Step 2 — Preview (Dry Run)

**Purpose**: Show exact changes without writing.

```
args: {sub_action: "rename", target_symbol, changes, dry_run: true}
```

**AI must check before proceeding:**
| Check | Must Be | If Not |
|-------|---------|--------|
| `validation_result.passed` | `true` | STOP — conflicts exist |
| `blast_radius.risk` | `low`/`medium` | Ask confirmation |
| `changes[]` | All expected | Investigate unexpected |

---

## Step 3 — Apply (User Confirmation)

**Only after user explicitly says "yes"**:

```
args: {sub_action: "rename", target_symbol, changes, dry_run: false}
```

### Post-Apply Checklist
1. **Sync index**: `repo:sync` → refresh graph
2. **Run tests**: `cb:test:run` → verify nothing broke
3. **Report**: Which files changed, commit hash

---

## Refactoring Types

### rename
```
args: {sub_action: "rename", target_symbol: "file.py::Symbol", changes: {new_name: "NewName"}}
```
AST-safe across all references, imports, callers. Auto-commits.

### move
```
args: {sub_action: "move", target_symbol: "old_file.py::Symbol", changes: {target_file: "new_file.py"}}
```
Smart placement: detects optimal insertion position.

### extract
```
args: {sub_action: "extract", target_symbol: "file.py::", changes: {new_name: "newFunc", line_start: 10, line_end: 25}}
```
Extracts to function with proper parameters.

### inline
```
args: {sub_action: "inline", target_symbol: "file.py::funcToInline"}
```
Use when function is called once or trivial.

### signature
```
args: {sub_action: "signature", target_symbol: "file.py::func",
       changes: {params_add: [{name:"p", type:"str"}], params_remove: ["old"]}}
```

### rename_file / move_file
```
args: {sub_action: "rename_file"|"move_file", target_symbol: "src/old.py",
       changes: {new_path: "src/new.py"}}
```

### modularize
```
args: {sub_action: "modularize", target_symbol: "src/monolith/", changes: {target_domain: "src/domain/"}}
```
AI-assisted domain clustering for monolith → services.

---

## Anti-Patterns

| Anti-Pattern | Why | Correct |
|-------------|-----|---------|
| Skip impact analysis | Blind blast radius | Always run `impact` |
| Skip dry_run | Unexpected changes | Always preview |
| Apply without confirmation | AI shouldn't write autonomously | Get explicit "yes" |
| Ignore `validation_result.passed=false` | Conflicts break build | Fix conflicts first |
| Not syncing after apply | Stale graph | Run `repo:sync` |
| Not running tests after apply | Silent regressions | Run `cb:test:run` |

---

## Undo Support

- Auto-commits per operation
- Rollback: `repo:git action=git args={subcommand:"reset", args:["HEAD~1"]}`
- Or use CLI: `codecortex cg refactor <repo_id> undo`

---

## Deliverable Format

```markdown
# Refactor Report
- **Target**: `src/service.py::process_order` → `process_order_v2`
- **Risk**: low · **Files**: 3 · **Symbols**: 5
- **Validation**: passed · **Warnings**: none
- **Commit**: abc123def
- **Post-Apply Tests**: 5/5 passed
```

---

## Token Economy

| Technique | Saved | How |
|-----------|-------|-----|
| `dry_run:true` before apply | ~100% mistakes | Prevents costly reverts |
| `limit:10` on impact results | ~40% | Cap file list |
| Skip tests if no coverage | ~25% | Check coverage first |

---

## CLI Equivalents

See `docs/guides/how-to-use-cli.md`:
```bash
codecortex ref impact <target> --new-name <name>
codecortex ref rename <target> --new-name <name>
codecortex ref move <target> --target-file <file>
codecortex ref extract <file> --line-start 10 --line-end 25 --new-name func
```

---

## Feature Docs

| Resource | Path |
|----------|------|
| Concept | `docs/features/coderefactor/concept.md` |
| AI-Impact | `docs/features/coderefactor/ai-impact-token-efficiency.md` |
| Examples | `docs/features/coderefactor/examples/` |
| Workflow | `docs/workflows/safe-refactoring-workflow.md` |
