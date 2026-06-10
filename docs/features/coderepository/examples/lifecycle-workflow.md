# Repository Lifecycle Workflow Example

This example demonstrates a typical repository lifecycle workflow using CodeRepository tools.

## 1. Initialize Repository

Clone a remote repository, index it, and run security audit:

```json
{
  "tool": "repo_init",
  "repo_path": "/projects/myapp",
  "remote_url": "https://github.com/user/myapp.git",
  "run_audit": true
}
```

**Expected AI Actions:**
- Initialization confirmation with file count
- Security findings alert (if any critical/high issues)
- Analysis recommendation for large codebases
- Health monitoring workflow guidance

## 2. Check Repository Health

Fast health check without heavy parsing:

```json
{
  "tool": "repo_inspect",
  "repo_path": "/projects/myapp",
  "include_git_diagnostics": true,
  "include_file_stats": true
}
```

**Expected AI Actions:**
- Health score (0-100) with interpretation
- VCS metrics (churn, bus factor, velocity)
- Dependency summary
- Next step suggestions

## 3. Full Semantic Analysis

Build call graphs and enable search:

```json
{
  "tool": "repo_analyze",
  "repo_path": "/projects/myapp",
  "build_graph": true,
  "store_embeddings": true
}
```

**Expected AI Actions:**
- Analysis summary (symbols, edges extracted)
- Complexity alerts for high-complexity files
- Entry point identification
- Search and refactor recommendations

## 4. Incremental Sync

Sync only changed files after code updates:

```json
{
  "tool": "repo_sync",
  "repo_path": "/projects/myapp",
  "mode": "auto",
  "dry_run": false
}
```

**Expected AI Actions:**
- Sync summary (files added/modified/deleted)
- Symbol/edge change counts
- Analysis recommendation for updated files
- Orphaned data removal notifications

## 5. Check Staleness

Verify if repository needs sync:

```json
{
  "tool": "repo_staleness",
  "repo_path": "/projects/myapp",
  "compare_remote": true,
  "fetch_remote": false
}
```

**Expected AI Actions:**
- Staleness level (fresh/behind/ahead/diverged/dirty/outdated)
- Commit counts (behind/ahead)
- Working tree changes alert
- Sync recommendation with command hint

## 6. Commit History Analysis

Analyze commit history and author statistics:

```json
{
  "tool": "repo_history",
  "repo_path": "/projects/myapp",
  "limit": 100,
  "include_stats": true
}
```

**Expected AI Actions:**
- Commit count and VCS type
- Top contributor identification
- Integration recommendations (repo_inspect, repo_analyze, repo_audit)
- Limit warning if truncated

## 7. Security Audit

Scan for secrets and vulnerabilities:

```json
{
  "tool": "repo_audit",
  "repo_path": "/projects/myapp",
  "detect_secrets": true,
  "include_git_history": true
}
```

**Expected AI Actions:**
- Critical/high severity alerts
- Remediation commands
- Re-audit recommendation after fixes

## 8. Export Backup

Create portable backup of repository data:

```json
{
  "tool": "repo_dump",
  "repo_path": "/projects/myapp",
  "format": "yaml",
  "split_by_type": true,
  "compress": true,
  "include_findings": true
}
```

**Expected AI Actions:**
- Export summary (records, files, size)
- Findings review warning
- Restore command
- Embeddings inclusion suggestion

## 9. List All Repositories

Discover all indexed repositories:

```json
{
  "tool": "repo_list",
  "include_metadata": true,
  "include_vcs_status": true,
  "limit": 50
}
```

**Expected AI Actions:**
- Orphaned repository alerts
- Stale repository identification
- Fleet size management tips
- Cleanup/sync recommendations

## 10. Cleanup Orphaned Repository

Remove data for deleted repository:

```json
{
  "tool": "repo_cleanup",
  "repo_path": "/projects/old-project",
  "dry_run": true
}
```

**Expected AI Actions:**
- Dry-run preview with record breakdown
- Safety warnings (path existence check)
- Force requirement reminder
- Deletion summary on actual run
