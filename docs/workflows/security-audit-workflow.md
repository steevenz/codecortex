---
description: Security & Compliance Audit — detect secrets, PII, vulnerabilities, and misconfigurations
title: WFK_SEC_001 — Security & Compliance Audit
workflow_id: WFK_SEC_001
version: 2.0.0
author: Steeven Andrian
standard: Aegis-Workflow-v2.0
codification: Aegis-Architecture-v1.0 §5
---

# WFK_SEC_001: Security & Compliance Audit

> **Goal**: Perform a multi-layer security assessment — code-level secrets, Git history leaks, file permissions, and architecture-level security patterns.
> **Trigger**: User asks for security audit, secret scan, vulnerability check, or compliance review.
> **Time**: 1-3 minutes.
> **Cost**: Medium (full scan of source + history + filesystem).
> **Standards**: Aegis-Security-v1.0, OWASP-aligned categories.

---

## 1. Trigger Phrases

- *"Security audit"*
- *"Find secrets"*
- *"Check for vulnerabilities"*
- *"Compliance check"*
- *"OWASP scan"*
- *"Secret leak check"*
- *"Is there a hardcoded API key?"*
- *"PII scan"*
- *"Security review"*
- *"Are we leaking credentials?"*

---

## 2. Pipeline Overview

```
Step 1: Code-Level Audit   (cb:audit)        ───┐
Step 2: Git History Audit   (repo:audit)     ───┤
Step 3: File Security       (fs:audit)      ───┤───► Deliverable
Step 4: Architecture Audit  (cb:graph:audit) ───┘
```

---

## 3. Step 1 — Code-Level Security Audit

**Purpose**: Scan source code for secrets, PII, misconfigurations, vulnerabilities, DI violations.

### MCP Call
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: ".",
    scan_categories: ["secrets", "pii", "misconfig", "vulns", "naming", "di_compliance"],
    severity_threshold: "low",
    entropy_threshold: 4.5,
    max_file_size_kb: 1024,
    files: null,
    use_ast: true,
    use_aiignore: true,
    since: null
  }
```

### Scan Categories Explained
| Category | Detects | Example |
|----------|---------|---------|
| `secrets` | Hardcoded API keys, tokens, passwords | `API_KEY = "sk-..."` |
| `pii` | Personal Identifiable Information | Emails, phone numbers, SSNs |
| `misconfig` | Dangerous configuration | `debug=True` in production |
| `vulns` | Known vulnerability patterns | SQL injection, XSS sinks |
| `naming` | Naming convention violations | `password` in variable name (leak risk) |
| `di_compliance` | Dependency injection violations | Hardcoded `new Database()` |

### AI Must Read
| Field | Priority |
|-------|----------|
| `compliance_score` | Overall health (0-100). `< 70` → significant issues. |
| `findings[].severity` | `critical` > `high` > `medium` > `low` |
| `findings[].confidence` | `> 0.9` → almost certainly a real issue. |
| `findings[].category` | Group by category for the deliverable. |
| `findings[].code` | Exact offending line — quote in report. |
| `findings[].remediation` | Suggest this as the fix. |
| `findings[].standard_ref` | Reference Aegis standard violated. |
| `recommendations[]` | High-level fixes from CodeCortex. |

### Incremental Audit
For repeated audits, use `since` to only scan changes:
```
MCP: codecortex:codebase
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    target: ".",
    scan_categories: ["secrets", "vulns"],
    since: "2026-05-20T00:00:00Z"
  }
```

### CLI
```bash
codecortex cb audit /path/to/project --severity-threshold low --use-ast
codecortex cb audit /path/to/project --categories secrets,pii --since 2026-05-20
```

---

## 4. Step 2 — Git History Audit

**Purpose**: Scan Git history for secrets that were committed and later "removed" (still in history).

### MCP Call
```
MCP: codecortex:repository
  action: "audit"
  repo_id: "<repo_id>"
  args: {
    secrets: true,
    include_git_history: true,
    scope: {
      exclude: ["vendor/", "node_modules/", "dist/", ".git/"]
    }
  }
```

### Why This Matters
Even if a secret was deleted from the current working tree, it may still exist in Git history. Attackers can extract secrets from old commits.

### AI Must Read
| Field | Action |
|-------|--------|
| `findings[].commit` | The commit hash where secret was introduced. |
| `findings[].author` | Who committed it. |
| `findings[].file` | File path at that commit. |
| `findings[].secret_type` | `api_key`, `password`, `token`, `private_key` |

### Remediation for History Leaks
If secrets found in history:
1. Rotate the credential immediately.
2. Use `git filter-repo` or BFG Repo-Cleaner to purge from history.
3. Force-push after cleaning (coordinate with team).

### CLI
```bash
codecortex repo audit /path/to/project --secrets --include-git-history
```

---

## 5. Step 3 — File Security Audit

**Purpose**: Scan filesystem metadata — sensitive filenames, permissions, hidden files.

### MCP Call
```
MCP: codecortex:filesystem
  action: "audit"
  path: "<repo_path>"
  args: {
    recursive: true,
    severity: "low",
    check_permissions: true,
    check_hidden: true,
    max_file_size_mb: 100,
    exclude_patterns: ["*.log", "*.tmp"],
    limit: 200
  }
```

### Detection Categories
| Category | Examples | Severity |
|----------|----------|----------|
| `sensitive_file` | `.env`, `credentials.json`, `id_rsa` | critical |
| `permission` | `777` on source files | high |
| `hidden_vcs` | `.svn/`, `.hg/` exposed | medium |
| `large_file` | Files > 100MB in repo | low |

### AI Must Read
| Field | Action |
|-------|--------|
| `findings[].category` | Prioritize `sensitive_file` and `permission`. |
| `findings[].path` | Exact file to report. |
| `findings[].recommendation` | Suggest `.gitignore`, `chmod`, or deletion. |

### CLI
```bash
codecortex fs audit /path/to/project --recursive --severity low
```

---

## 6. Step 4 — Architecture Security Patterns

**Purpose**: Detect security anti-patterns at the architecture level — insecure module boundaries, excessive coupling in auth paths.

### MCP Call
```
MCP: codecortex:codebase
  action: "graph"
  repo_id: "<repo_id>"
  args: {
    sub_action: "audit",
    audit_types: ["security", "coupling", "complexity"],
    degree_threshold: 10,
    include_summary: true,
    limit: 50
  }
```

### Security-Focused Graph Checks
| Check | Risk | Action |
|-------|------|--------|
| Auth module coupled to `utils.py` | `coupling.score > 0.7` | Flag: auth should be isolated |
| `UserService` is a god node | `in_degree > 30` | Split into smaller services |
| Circular deps in auth flow | `circular_deps.count > 0` | Break cycle to prevent deadlocks |

### CLI
```bash
codecortex cg audit <repo_id> --types security,coupling,complexity
```

---

## 7. Deliverable Format

```markdown
# Security & Compliance Audit Report

## Overall Compliance Score: <N>/100

## 1. Critical Findings (Must Fix Immediately)
| # | Category | File | Line | Issue | Fix |
|---|----------|------|------|-------|-----|
| 1 | secrets | `src/config.py` | 42 | Hardcoded API key | Move to env var |
| 2 | pii | `src/models.py` | 15 | SSN in model | Anonymize / encrypt |

## 2. High Findings (Fix Before Next Release)
| # | Category | File | Issue | Fix |
|---|----------|------|-------|-----|
| ... | ... | ... | ... | ... |

## 3. Medium Findings (Address in Next Sprint)
| # | Category | File | Issue | Fix |
|---|----------|------|-------|-----|
| ... | ... | ... | ... | ... |

## 4. Git History Leaks
| Commit | Author | File | Secret Type | Action |
|--------|--------|------|-------------|--------|
| `a1b2c3d` | dev@x.com | `config.py` | API key | Rotate + purge history |

## 5. File Security
| File | Category | Severity | Recommendation |
|------|----------|----------|----------------|
| `.env` | sensitive_file | critical | Add to `.gitignore` |
| `src/` | permission=777 | high | `chmod 755 src/` |

## 6. Architecture Security
| Issue | Module | Score | Recommendation |
|-------|--------|-------|----------------|
| Auth coupled to utils | auth → utils | 0.85 | Extract auth utilities |

## 7. Remediation Plan
### Immediate (24h)
- <critical items>

### Short-term (1 week)
- <high items>

### Long-term (1 month)
- <medium items>

## 8. Compliance Status
- [ ] **PASS** — No critical/high findings.
- [ ] **CONDITIONAL** — Critical fixed, highs pending.
- [ ] **FAIL** — Critical findings present. Do not deploy.
```

---

## 8. Standards Mapping

| Aegis Standard | Audit Category | Check |
|----------------|----------------|-------|
| Aegis-Security-v1.0 §3.1 | secrets | No hardcoded credentials |
| Aegis-Security-v1.0 §3.2 | pii | PII encrypted at rest |
| Aegis-Security-v1.0 §4.1 | misconfig | debug disabled in prod |
| Aegis-Security-v1.0 §5.1 | vulns | No known vulnerability patterns |
| Aegis-Architecture-v1.0 §2.3 | di_compliance | Constructor injection only |

---

## 9. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| `scan_categories` limited to relevant ones | ~30% | Don't scan all categories if user only asks for secrets |
| `severity_threshold: "medium"` vs "low" | ~40% | Filter low-confidence findings |
| `since` parameter for repeated audits | ~60% | Only scan changed files |
| `max_file_size_kb: 512` vs 1024 | ~20% | Skip oversized generated files |

### Parallel Execution
- Step 1 (`cb:audit`) + Step 2 (`repo:audit`) + Step 3 (`fs:audit`) are fully parallel
- Step 4 (`cb:graph:audit`) depends on graph being built, but can run parallel with Step 1 if graph exists

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| User asks "any hardcoded API keys?" | Run Step 1 with `scan_categories: ["secrets"]` only |
| `compliance_score == 100` after Step 1 | Skip Steps 2-4, deliver immediately |
| No `package.json`, `requirements.txt`, etc. | Skip `dependency_summary` check |

### Cache Reuse
- If audit ran within 24h → use `since` to scan only changes
- If `repo:audit` (git history) ran before → skip unless new commits added
- Store `compliance_score` baseline; re-audit only if code changed

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [analysis-orchestra-workflow.md](analysis-orchestra-workflow.md)*
