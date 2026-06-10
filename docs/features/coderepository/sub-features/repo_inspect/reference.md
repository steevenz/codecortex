# repo_inspect — Fast Repository Health Check

> **Source:** `src/domain/coderepository/api/tools.py`
> **Since:** 2026-05-24

## Overview

`repo_inspect` is a **lightweight repository health check** — no AST parsing, no file content reading. It runs non-invasive VCS diagnostics and returns a comprehensive snapshot in < 2 seconds.

## When to Use

- **Before coding session**: "Show me the current state of the repo"
- **After `repo_init`**: "Verify everything is ready"
- **Before major refactor**: "Which files are most risky to change?"
- **Onboarding**: "Give me a structural overview"

## Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_path` | string | ✅ | — | Absolute path to the repository |
| `repo_id` | string | ❌ | — | Alternative to `repo_path` (UUID) |
| `include_git_diagnostics` | boolean | ❌ | `true` | Run 5 git diagnostics: churn hotspots, bus factor, bug magnets, commit velocity, crisis frequency |
| `include_svn_diagnostics` | boolean | ❌ | `false` | Run SVN diagnostics if SVN detected |
| `include_index_metadata` | boolean | ❌ | `true` | Include index info if previously indexed |
| `include_vcs_status` | boolean | ❌ | `true` | Branch, ahead/behind, dirty state |
| `include_file_stats` | boolean | ❌ | `true` | File statistics by extension (source, config, doc, binary) |
| `include_dependency_summary` | boolean | ❌ | `false` | Scan package managers (package.json, Cargo.toml, go.mod, etc.) |
| `include_temporal_coupling` | boolean | ❌ | `false` | Analyze git co-change for temporal coupling (hidden dependencies) |
| `temporal_coupling_period` | string | ❌ | `"1_year"` | `"1_year"`, `"6_months"`, or `"90_days"` |
| `include_documentation` | boolean | ❌ | `false` | Scan and parse docs/ directory for PRDs, ADRs, specs |
| `diagnostic_period` | string | ❌ | `"1_year"` | `"1_year"`, `"6_months"`, or `"90_days"` |
| `output_format` | string | ❌ | `"json"` | `"json"` or `"markdown"` |
| `timeout_seconds` | integer | ❌ | `30` | Max execution time |

## 5 Git Diagnostics

| Diagnostic | Command | Output |
|------------|---------|--------|
| **Churn Hotspots** | `git log --name-only --since=<period>` | Top 20 most modified files with risk (high/medium/low) |
| **Bus Factor** | `git shortlog -sn --since=<period>` | Contributor distribution %, risk level |
| **Bug Magnets** | `git log --grep="fix\|bug" --since=<period>` | Files with most bug-related commits |
| **Commit Velocity** | `git log --date=short --since=<period>` | Commits per month + trend (increasing/steady/decreasing) |
| **Crisis Frequency** | `git log --grep="revert\|hotfix" --since=<period>` | Total reverts/hotfixes + risk level |

## Advanced Features

### Temporal Coupling Analysis (include_temporal_coupling)

When `include_temporal_coupling=true`, `repo_inspect` analyzes git co-change patterns to identify hidden dependencies between files that frequently change together.

**Parameters:**
- `include_temporal_coupling`: Enable temporal coupling analysis
- `temporal_coupling_period`: Time window - `"1_year"`, `"6_months"`, or `"90_days"`

**Output:**
```json
{
  "temporal_coupling": {
    "built": true,
    "period": "1 year",
    "total_pairs": 45,
    "hotspots": [
      {
        "file": "src/auth/handler.py",
        "co_change_partners": 8,
        "avg_score": 0.32,
        "risk": "high"
      }
    ]
  }
}
```

**Use Case:** Identify files that should be refactored together to reduce hidden dependencies and improve modularity.

### Documentation Intelligence (include_documentation)

When `include_documentation=true`, `repo_inspect` scans the `docs/` directory for:
- PRDs (Product Requirements Documents)
- ADRs (Architecture Decision Records)
- Specs (Technical specifications)
- README files

**Output:**
```json
{
  "documentation": {
    "total_documents": 12,
    "total_decisions": 5,
    "total_requirements": 8,
    "files_by_type": {
      "prd": 3,
      "adr": 5,
      "spec": 4
    },
    "readme": {
      "exists": true,
      "title": "Project README",
      "sections": ["Installation", "Usage", "Contributing"]
    }
  }
}
```

**Use Case:** Assess documentation completeness and architectural decision tracking for AI context understanding.

## Flow

```
STEP 1: Validate path + detect VCS type (.git → git, .svn → svn)
STEP 2: Query index metadata from SQLite (if previously repo_init'd)
STEP 3: VCS status — git status --porcelain, ahead/behind tracking
STEP 4: File statistics — os.walk, classify by extension (no AST)
STEP 5: Dependency summary — scan for package.json, Cargo.toml, etc.
STEP 6: Git diagnostics — churn, bus factor, bug magnets, velocity, crisis
STEP 6b: Temporal coupling (optional) — analyze git co-change for hidden dependencies
STEP 6c: Documentation intelligence (optional) — scan docs/ for PRDs, ADRs, specs
STEP 7: AI Readiness Score (0-100) + recommendations
STEP 8: Format output (JSON or Markdown)
```

## AI Readiness Score (0-100)

| Factor | Points |
|--------|--------|
| Under version control (git/svn) | +15 |
| Indexed by CodeCortex | +20 |
| > 10 source code files | +10 |
| Manageable size (< 1000 files) | +5 |
| High bus factor risk (>60% single contributor) | -10 |
| Medium bus factor risk (40-60%) | -5 |
| High churn hotspot | -5 |
| High crisis frequency | -5 |

## Response Examples

### Full JSON Output

```json
{
  "success": true,
  "data": {
    "repo_path": "/home/user/project",
    "vcs_type": "git",
    "vcs_branch": "main",
    "vcs_status": {
      "has_uncommitted_changes": false,
      "commits_ahead": 2,
      "commits_behind": 0
    },
    "index_metadata": {
      "indexed": true,
      "last_indexed_at": "2026-05-24T15:30:00Z",
      "total_files_indexed": 187,
      "total_symbols_indexed": 1240,
      "total_edges": 1987,
      "language_stats": {"python": 98, "typescript": 56}
    },
    "file_statistics": {
      "total_files": 245,
      "total_size_mb": 125.45,
      "avg_size_kb": 512.5,
      "largest_files": [{"path": "bundle.js", "size_mb": 12.3}],
      "breakdown": {"source_code_files": 187, "config_files": 12, "documentation": 8, "binaries": 6, "others": 32}
    },
    "git_diagnostics": {
      "churn_hotspots": [
        {"file": "src/auth/handler.py", "change_count": 234, "risk": "high"}
      ],
      "bus_factor": {"total_contributors": 8, "top_contributor_percentage": 45.2, "bus_factor_risk": "medium"},
      "bug_magnets": [{"file": "src/auth/handler.py", "bug_commits": 34}],
      "commit_velocity": {"commits_per_month_avg": 45.2, "trend": "steady"},
      "crisis_frequency": {"reverts_and_hotfixes": 20, "crisis_risk": "low"}
    },
    "insights": {
      "ai_readiness_score": 78,
      "recommended_actions": [
        {"severity": "warning", "message": "'src/auth/handler.py' is a churn hotspot. Consider refactoring."}
      ]
    }
  }
}
```

### Markdown Output

When `output_format="markdown"`, the response includes a Markdown report in `data.markdown`:

```json
{
  "success": true,
  "data": {
    "markdown": "# Repository Inspection Report\n\n**Repository:** `/home/user/project`...",
    "raw": { "...": "..." }
  }
}
```

The rendered Markdown looks like:

```markdown
# Repository Inspection Report

**Repository:** `/home/user/project`
**VCS:** git (branch: main)

## Index Status
- ✅ Indexed: 2026-05-24 15:30:00
- 📄 187 files, 🔧 1240 symbols, 🌐 1987 edges

## File Statistics
- Total files: 245, Size: 125.45 MB
- Source: 187, Config: 12, Docs: 8, Binaries: 6

## Git Diagnostics
- 🔴 src/auth/handler.py: 234 changes
- **Bus Factor:** 45.2% by top contributor, risk: medium
- **Commit Velocity:** Avg 45.2/month, trend: steady

## AI Readiness Score: 78/100
```

### Plain Directory (unindexed)

```json
{
  "success": true,
  "data": {
    "repo_path": "/home/user/scratch",
    "vcs_type": "none",
    "index_metadata": {"indexed": false},
    "file_statistics": {"total_files": 45, "total_size_mb": 12.3},
    "insights": {
      "ai_readiness_score": 50,
      "recommended_actions": [
        {"severity": "info", "message": "This directory is not under version control."},
        {"severity": "info", "message": "Repository is not indexed. Run `repo_init`."}
      ]
    }
  }
}
```

## Error Cases

| Error | Status | Message |
|-------|--------|---------|
| Path does not exist | `404` | `"Repository path does not exist or is not accessible"` |
| Timeout | `408` | Implicit via `timeout_seconds` |
