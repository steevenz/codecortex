# Repository Domain - Multi-Scenario Test Cases

**Date:** 2026-05-28  
**Tester:** QA Expert (Cascade)  
**Scope:** 13 repository MCP tools with comprehensive scenario coverage  
**Focus:** Deep testing for AI Coder assistance quality

---

## Test Strategy

For each tool, I'll design scenarios covering:
- **Happy Path:** Normal successful operations
- **Edge Cases:** Boundary conditions, unusual inputs
- **Error Handling:** Invalid inputs, missing parameters
- **Integration:** Cross-tool dependencies
- **AI Coder Impact:** How output helps AI coders

---

## Tool 1: repo_init (11 parameters)

### Scenario 1.1: Clone remote Git repository with audit
**Purpose:** Standard setup for remote repository
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "vcs_type": "git",
  "remote_url": "https://github.com/example/test-repo.git",
  "create_new": true,
  "run_audit": true
}
```
**Expected:** 200 OK, repo_id returned, audit findings included
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Essential for starting work on remote projects

### Scenario 1.2: Initialize local Git repository without remote
**Purpose:** Setup for local development
**Input:**
```json
{
  "repo_path": "/tmp/local-repo",
  "vcs_type": "git",
  "create_new": true,
  "run_audit": false
}
```
**Expected:** 200 OK, repo_id returned, no audit
**AI Coder Impact:** ⭐⭐⭐⭐ - Good for local project setup

### Scenario 1.3: Re-index existing repository with force
**Purpose:** Update index after major changes
**Input:**
```json
{
  "repo_path": "/tmp/existing-repo",
  "force": true,
  "run_audit": false
}
```
**Expected:** 200 OK, old data cleaned, new index created
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Critical for keeping AI context current

### Scenario 1.4: Initialize directory without VCS
**Purpose:** Index non-versioned code
**Input:**
```json
{
  "repo_path": "/tmp/no-vcs",
  "vcs_type": "none",
  "create_new": true,
  "run_audit": false
}
```
**Expected:** 200 OK, repo_id returned, no VCS metadata
**AI Coder Impact:** ⭐⭐⭐ - Useful for quick scans without VCS

### Scenario 1.5: Clone with custom include/exclude patterns
**Purpose:** Targeted indexing
**Input:**
```json
{
  "repo_path": "/target/repo",
  "remote_url": "https://github.com/example/repo.git",
  "include_patterns": ["*.py", "*.ts"],
  "exclude_patterns": ["node_modules", "__pycache__"],
  "create_new": true
}
```
**Expected:** 200 OK, only specified files indexed
**AI Coder Impact:** ⭐⭐⭐⭐ - Optimizes for specific tech stack

### Scenario 1.6: Path already exists without force (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/existing-dir",
  "create_new": false,
  "force": false
}
```
**Expected:** 409 Conflict, message to use force=true
**AI Coder Impact:** ⭐⭐ - Clear error message guides AI to retry

### Scenario 1.7: Path missing without create_new or remote (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/nonexistent",
  "create_new": false,
  "remote_url": null
}
```
**Expected:** 404 Not Found, message to use create_new=true or provide remote_url
**AI Coder Impact:** ⭐⭐ - Clear error message guides AI to correct

### Scenario 1.8: Invalid remote URL (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/test",
  "remote_url": "https://github.com/invalid/repo.git",
  "create_new": true
}
```
**Expected:** 400 Bad Request, git clone failed message
**AI Coder Impact:** ⭐⭐ - Clear error prevents AI from hanging

### Scenario 1.9: Parallel processing with custom workers
**Purpose:** Performance optimization
**Input:**
```json
{
  "repo_path": "/tmp/large-repo",
  "remote_url": "https://github.com/example/large-repo.git",
  "parallel": true,
  "max_workers": 8
}
```
**Expected:** 200 OK, faster indexing with 8 workers
**AI Coder Impact:** ⭐⭐⭐⭐ - Speeds up initial setup for large repos

### Scenario 1.10: Custom audit categories
**Purpose:** Targeted security scanning
**Input:**
```json
{
  "repo_path": "/tmp/repo",
  "run_audit": true,
  "audit_categories": ["secrets", "vulns"]
}
```
**Expected:** 200 OK, only secrets and vulns scanned
**AI Coder Impact:** ⭐⭐⭐⭐ - Focused security assessment

---

## Tool 2: repo_inspect (12 parameters)

### Scenario 2.1: Basic inspection (default parameters)
**Purpose:** Quick health check
**Input:**
```json
{
  "repo_path": "/tmp/test-repo"
}
```
**Expected:** 200 OK, metadata, git diagnostics, file stats, AI readiness score
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Essential for understanding repo state before coding

### Scenario 2.2: Full inspection with all diagnostics
**Purpose:** Comprehensive analysis
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "include_git_diagnostics": true,
  "include_svn_diagnostics": false,
  "include_index_metadata": true,
  include_vcs_status": true,
  "include_file_stats": true,
  "include_dependency_summary": true
}
```
**Expected:** 200 OK, all diagnostics included
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Complete picture for AI decision making

### Scenario 3.2: Inspect by repo_id instead of path
**Purpose:** Alternative lookup
**Input:**
```json
{
  "repo_id": "f8a3d2e1-4b5c-6d7e-8f9a-0b1c2d3e4f5a"
}
```
**Expected:** 200 OK, metadata for specific repo
**AI Coder Impact:** ⭐⭐⭐⭐ - Enables repo switching by ID

### Scenario 2.3: Markdown output for human readability
**Purpose:** Human-friendly report
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "output_format": "markdown"
}
```
**Expected:** 200 OK, markdown report in data.markdown field
**AI Coder Impact:** ⭐⭐⭐ - Good for presenting to user

### Scenario 2.4: Custom diagnostic period
**Purpose:** Historical analysis window
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "diagnostic_period": "90_days"
}
```
**Expected:** 200 OK, diagnostics limited to 90 days
**AI Cartner Impact:** ⭐⭐⭐ - Focused recent history

### Scenario 2.5: Temporal coupling analysis (undocumented feature)
**Purpose:** Identify co-changing files
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "include_temporal_coupling": true,
  "temporal_coupling_period": "6_months"
}
```
**Expected:** 200 OK, temporal coupling data included
**AI Coder Impact:** ⭐⭐⭐⭐ - Identifies risky dependencies

### Scenario 2.6: Documentation scanning (undocumented feature)
**Purpose:** Extract PRDs, ADRs, specs
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "include_documentation": true
}
```
**Expected:** 200 OK, documentation metadata included
**AI Coder Impact:** ⭐⭐⭐⭐ - Enables architecture understanding

### Scenario 2.7: Non-existent path (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/nonexistent"
}
```
**Expected:** 404 Not Found
**AI Coder Impact:** ⭐⭐ - Clear error prevents confusion

### Scenario 2.8: Timeout handling
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/slow-repo",
  "timeout_seconds": 5
}
```
**Expected:** 408 Timeout or partial results
**AI Coder Impact:** ⭐⭐ - Prevents hanging

---

## Tool 3: repo_analyze (16 parameters)

### Scenario 3.1: Full analysis with graph building
**Purpose:** Deep semantic analysis
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "build_graph": true,
  "graph_relations": ["calls", "imports", "inherits"],
  "extract_symbols": true
}
```
**Expected:** 200 OK, graph built, symbols extracted
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Enables code search and refactoring

### Scenario 3.2: Incremental analysis (faster for large repos)
**Purpose:** Performance optimization
**Input:**
```json
{
  "repo_path": "/tmp/large-repo",
  "incremental": true,
  "force": false
}
```
**Expected:** 200 OK, only changed files re-indexed
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Faster updates for large repos

### Scenario 3.3: Force full re-index
**Purpose:** Complete rebuild
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "force": true,
  "incremental": false
}
```
**Expected:** 200 OK, entire index rebuilt
**AI Coder Impact:** ⭐⭐⭐⭐ - Ensures fresh context

### Scenario 3.4: Language-specific analysis
**Purpose:** Targeted analysis
**Input:**
```json
{
  "repo_path": "/tmp/multi-lang-repo",
  "languages": ["python", "go"],
  "include_patterns": ["*.py", "*.go"]
}
```
**Expected:** 200 OK, only Python and Go analyzed
**AI Coder Impact:** ⭐⭐⭐⭐ - Optimized for polyglot projects

### Scenario 3.5: Vector embeddings for semantic search
**Purpose:** Enable semantic search
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "store_embeddings": true,
  "embedding_model": "codebert"
}
```
**Expected:** 200 OK, embeddings generated
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Enables semantic code search

### Scenario 3.6: Neo4j graph backend
**Purpose:** Advanced graph queries
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "graph_backend": "neo4j"
}
```
**Expected:** 200 OK, graph stored in Neo4j
**AI Coder Impact:** ⭐⭐⭐⭐ - Advanced graph queries

### Scenario 3.7: Dry-run simulation
**Purpose:** Preview analysis without writing
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "dry_run": true
}
```
**Expected:** 200 OK, changes previewed but not committed
**AI Coder Impact:** ⭐⭐⭐⭐ - Safe preview before expensive operation

### Scenario 3.8: File size limit
**Purpose:** Performance optimization
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "max_file_size_kb": 100
}
```
**Expected:** 200 OK, large files skipped
**AI Coder Impact:** ⭐⭐⭐ - Prevents memory issues

### Scenario 3.9: Non-existent path (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/nonexistent"
}
```
**Expected:** 404 Not Found
**AI Coder Impact:** ⭐⭐ - Clear error message

---

## Tool 4: repo_sync (7 parameters)

### Scenario 4.1: Auto sync (default)
**Purpose:** Incremental sync with auto-detection
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "mode": "auto"
}
```
**Expected:** 200 OK, changes detected and applied
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Keeps index current automatically

### Scenario 4.2: Full sync (re-scan all)
**Purpose:** Complete re-index
**Input:```
```json
{
  "repo_path": "/tmp/test-repo",
  "mode": "full"
}
```
**Expected:** 200 OK, all files re-scanned
**AI Coder Impact:** ⭐⭐⭐⭐ - Ensures complete accuracy

### Scenario 4.3: Fast sync (check only)
**Purpose:** Quick staleness check
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "mode": "fast"
}
```
**Expected:** 200 OK, changes detected but not applied
**AI Coder Impact:** ⭐⭐⭐⭐ - Quick check before expensive operations

### Scenario 4.4: Dry-run preview
**Purpose:** Preview changes
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "dry_run": true
}
```
**Expected:** 200 OK, change plan returned but not applied
**AI Coder Impact:** ⭐⭐⭐⭐ - Safe preview before sync

### Scenario 4.5: Sync without reindexing
**Purpose:** Fast metadata-only sync
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "reindex_updated": false
}
```
**Expected:** 200 OK, metadata updated but symbols not re-indexed
**AI Coder Impact:** ⭐⭐⭐ - Fast metadata updates

### Scenario 4.6: Sync without deletion
**Purpose:** Preserve deleted files in index
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "remove_deleted": false
}
```
**Expected:** 200 OK, deleted files kept in index
**AI Coder Impact:** ⭐⭐⭐ - Preserves historical context

### Scenario 4.7: Non-existent repo (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/nonexistent"
}
```
**Expected:** 404 Not Found
**AI Coder Impact:** ⭐⭐ - Clear error message

---

## Tool 5: repo_audit (15 parameters)

### Scenario 5.1: Full security audit (default)
**Purpose:** Comprehensive security scan
**Input:**
```json
{
  "repo_path": "/tmp/test-repo"
}
```
**Expected:** 200 OK, secrets, PII, misconfig, vulns scanned
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Critical for security awareness

### Scenario 5.2: Secrets-only scan
**Purpose:** Focused security check
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "detect_secrets": true,
  "detect_pii": false,
  "detect_misconfig": false,
  "detect_vuln_patterns": false,
  "detect_weak_crypto": false
}
```
**Expected:** 200 OK, only secrets detected
**AI Coder Impact:** ⭐⭐⭐⭐ - Focused security check

### Scenario 5.3: PII detection
**Purpose:** Privacy compliance
**Input:```
```json
{
  "repo_path": "/tmp/test-repo",
  "detect_pii": true
}
```
**Expected:** 200 OK, email, phone, SSN detected
**AI Coder Impact:** ⭐⭐⭐ - Privacy compliance check

### Scenario 5.4: Git history scan
**Purpose:** Historical security check
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "include_git_history": true
}
```
**Expected:** 200 OK, git history scanned for secrets
**AI Coder Impact:** ⭐⭐⭐⭐ - Historical security awareness

### Scenario 5.5: LLM validation (requires API key)
**Purpose:** Reduce false positives
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "use_llm_validation": true,
  "llm_model": "claude-3.5-sonnet"
}
```
**Expected:** 200 OK, findings validated by LLM
**AI Coder Impact:** ⭐⭐⭐⭐ - Higher confidence in findings

### Scenario 5.6: Custom scan categories
**Purpose:** Targeted security check
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "scan_categories": ["secrets", "vulns"]
}
```
**Expected:** 200 OK, only specified categories scanned
**AI Coder Impact:** ⭐⭐⭐⭐ - Focused security assessment

### Scenario 5.7: Large file limit
**Purpose:** Performance optimization
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "max_file_size_kb": 512
}
```
**Expected:** 200 OK, large files skipped
**AI Coder Impact:** ⭐⭐⭐ - Performance optimization

### Scenario 5.8: Markdown output
**Purpose:** Human-readable report
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "output_format": "markdown"
}
```
**Expected:** 200 OK, markdown report in data.markdown field
**AI Coder Impact:** ⭐⭐⭐ - Good for presenting to user

### Scenario 5.9: Non-existent path (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/nonexistent"
}
```
**Expected:** 404 Not Found
**AI Coder Impact:** ⭐⭐ - Clear error message

---

## Tool 6: repo_staleness (5 parameters)

### Scenario 6.1: Check staleness with remote comparison
**Purpose:** Determine if re-index needed
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "compare_remote": true
}
```
**Expected:** 200 OK, status (fresh/behind/ahead/diverged/dirty)
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Critical for deciding when to re-index

### Scenario 6.2: Fetch remote before comparison
**Purpose:** Get latest remote state
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "fetch_remote": true
}
```
Expected:** 200 OK, remote fetched then compared
**AI Coder Impact:** ⭐⭐⭐⭐ - Accurate remote comparison

### Scenario 6.3: Check local changes only
**Purpose:** Working tree analysis
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "compare_remote": false,
  "include_local_changes": true
}
```
**Expected:** 200 OK, only local changes checked
**AI Coder Impact:** ⭐⭐⭐ - Working tree awareness

### Scenario 6.4: Non-existent path (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/nonexistent"
}
```
**Expected:** 404 Not Found
**AI Coder Impact:** ⭐⭐ - Clear error message

### Scenario 6.5: No VCS detected (error)
**Purpose:** Error handling
**Input:**
```json
{
  "repo_path": "/tmp/no-vcs-dir"
}
```
**Expected:** 400 Bad Request, no VCS detected
**AI Coder Impact:** ⭐⭐ - Clear error message

---

## Tool 7: repo_list (8 parameters)

### Scenario 7.1: List all repositories (default)
**Purpose:** Discover registered repos
**Input:**
```json
{
  "filter_status": "all"
}
```
**Expected:** 200 OK, all repos with metadata
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Essential for repo discovery

### Scenario 7.2: List only indexed repos
**Purpose:** Filter by status
**Input:**
```json
{
  "filter_status": "indexed"
}
```
**Expected:** 200 OK, only healthy repos returned
**AI Coder Impact:** ⭐⭐⭐⭐ - Filter for ready-to-use repos

### Scenario 7.3: List orphaned repos
**Purpose**: Maintenance
**Input:`
```json
{
  "filter_status": "orphaned"
}
```
Expected:** 200 OK, only deleted path repos returned
**AI Coder Impact:** ⭐⭐⭐ - Maintenance task

### Scenario 7.4: List with VCS status
**Purpose:** Real-time VCS awareness
**Input:**
```json
{
  "filter_status": "all",
  "include_vcs_status": true
}
```
Expected:** 200 OK, includes branch, ahead/behind, uncommitted
**AI Coder Impact:** ⭐⭐⭐⭐⭐ - Real-time VCS awareness

### Scenario 7.5: Pagination
**Purpose:** Handle large repo lists
**Input:**
```json
{
  "filter_status": "all",
  "limit": 10,
  "offset": 0
}
```
Expected:** 200 OK, first 10 repos returned
**AI Coder Impact:** ⭐⭐⭐ - Handles large repo collections

### Scenario 7.6: Custom sorting
**Purpose**: Ordered output
**Input:**
```json
{
  "filter_status": "all",
  "order_by": "last_analyzed",
  "order_dir": "desc"
}
```
Expected:** 200 OK, sorted by last analyzed
**AI Cartner Impact:** ⭐⭐⭐ - Prioritization

### Scenario 7.7: Markdown table output
**Purpose:** Human-readable list
**Input:**
```json
{
  "filter_status": "all",
  "output_format": "table"
}
```
**Expected:** 200 OK, markdown table in data.table field
**AI Coder Impact:** ⭐⭐⭐ - Good for presenting to user

### Scenario 7.8: No repos in database (error)
**Purpose:** Error handling
**Input:**
```json
{
  "filter_status": "all"
}
```
**Expected:** 404 Not Found, suggestion to run repo_init
**AI Coder Impact:** ⭐⭐ - Clear guidance for first-time setup

---

## Tool 8: repo_compact (7 parameters)

### Scenario 8.1: Compact entire database
**Purpose:** Database maintenance
**Input:**
```json
{}
```
**Expected:** 200 OK, entire DB compacted, snapshot exported
**AI Coder Impact:** ⭐⭐⭐ - Maintenance task

### Scenario 8.2: Compact single repository
**Purpose:** Targeted maintenance
**Input:**
```json
{
  "repo_path": "/tmp/test-repo"
}
```
**Expected:** 200 OK, only specified repo compacted
**AI Coder Impact:** ⭐⭐⭐ - Targeted maintenance

### Scenario 8.3: Export JSON snapshot
**Purpose:** Portable export
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "output_format": "json"
}
```
**Expected:** 200 OK, JSON snapshot exported
**AI Cartner Impact:** ⭐⭐⭐ - Portable backup

### Scenario 8.4: Custom snapshot path
**Purpose:** Custom export location
**Input:**
```json
{
  "repo_path": "/tmp/test-repo",
  "output_path": "/backup/snapshot.json"
}
```
**Expected:** 200 OK, snapshot at custom path
**AI Coder Impact:** ⭐⭐⭐ - Custom backup location

### Scenario 8.5: Dry-run preview
**Purpose:** Preview changes
**Input:```json
{
  "repo_path": /tmp/test-repo",
  "dry_run": true
}
```
**Expected:** 200 OK, would-remove counts returned
**AI Coder Impact:** ⭐⭐⭐⭐ - Safe preview before destructive operation

### Scenario 8.6: Disable VACUUM
**Purpose:** Faster operation
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "compact_db": false
}
```
**Expected:** 200 OK, cleanup but no VACUUM
**AI Coder Impact:** ⭐⭐ - Faster operation

### Scenario 8.7: Disable orphaned cleanup
**Purpose:** Preserve data
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "remove_orphaned": false
}
```
**Expected:** 200 OK, orphans kept
**AI Coder Impact:** ⭐⭐ - Data preservation

---

## Tool 9: repo_cleanup (5 parameters)

### Scenario 9.1: Cleanup by path
**Purpose:** Delete repo data
**Input:```json
{
  "repo_path": "/tmp/test-repo"
}
```
**Expected:** 200 OK, repo data deleted
**AI Coder Impact:** ⭐⭐⭐ - Project cleanup

### Scenario 9.2: Cleanup by repo_id
**Purpose:** Delete by ID
**Input:```json
{
  "repo_id": "f8a3d2e1-4b5c-6d7e-8f9a-0b1c2d3e4f5a"
}
```
**Expected:** 200 OK, repo data deleted
**AI Coder Impact:** ⭐⭐⭐ - ID-based cleanup

### Scenario 9.3: Delete with snapshot
**Purpose:** Delete all data including snapshot
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "delete_snapshot": true
}
```
**Expected:** 200 OK, snapshot also deleted
**AI Coder Impact:** ⭐⭐⭐ - Complete cleanup

### Scenario 9.4: Dry-run preview
**Purpose:** Preview deletion
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "dry_run": true
}
```
**Expected:** 200 OK, would-delete counts returned
**AI Coder Impact:** ⭐⭐⭐⭐ - Safe preview before destructive operation

### 9.5: Force cleanup (dangerous)
**Purpose:** Override safety checks
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "force": true
}
```
**Expected:** 200 OK, deleted without confirmation
**AI Coder Impact:** ⭐⭐ - Dangerous, use with caution

---

## Tool 10: repo_dump (8 parameters)

### Scenario 10.1: Dump all data
**Purpose:** Full export
**Input:```json
{
  "repo_path": "/tmp/test-repo"
}
```
**Expected:** 200 OK, all data exported
**AI Coder Impact:** ⭐⭐⭐⭐ - Complete backup

### Scenario 10.2: Dump with embeddings
**Purpose:** Include vector data
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "include_embeddings": true
}
```
**Expected:** 200 OK, embeddings included
**AI Coder Impact:** ⭐⭐⭐⭐ - Complete backup with semantic data

### Scenario 10.3: Dump without findings
**Purpose:** Exclude audit data
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "include_findings": false
}
```
**Expected:** 200 OK, findings excluded
**AI Coder Impact:** ⭐⭐⭐ - Clean data export

### Scenario 10.4: Custom output directory
**Purpose:** Custom export location
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "output_dir": "/backup/export"
}
```
**Expected:** 200 OK, data at custom path
**AI Coder Impact:** ⭐⭐⭐ - Custom backup location

### Scenario 10.5: Non-existent repo (error)
**Purpose:** Error handling
**Input:```json
{
  "repo_path": "/tmp/nonexistent"
}
```
**Expected:** 404 Not Found
**AI Coder Impact:** ⭐⭐ - Clear error message

---

## Tool 11: repo_restore (5 parameters)

### Scenario 11.1: Restore from dump
**Purpose:** Import backup
**Input:```json
{
  "source": "/backup/snapshot.yaml",
  "repo_path": "/tmp/test-repo"
}
```
**Expected:** 200 OK, data restored
**AI Coder Impact:** ⭐⭐⭐⭐ - Restore from backup

### 11.2: Restore with overwrite
**Purpose:** Overwrite existing data
**Input:```json
{
  "source": "/backup/snapshot.yaml",
  "repo_path": "/tmp/test-repo",
  "overwrite": true
}
```
Expected:** 200 OK, existing data overwritten
AI Coder Impact:** ⭐⭐⭐ - Restore with overwrite

### 11.3: Restore with checksum verification
**Purpose:** Data integrity check
**Input:```json
{
  "source": "/backup/snapshot.yaml",
  "verify_checksum": true
}
```
Expected:** 200 OK, checksum verified
AI Coder Impact:** ⭐⭐⭐⭐ - Data integrity guaranteed

### 11.4: Dry-run preview
**Purpose:** Preview restore
Input:```json
{
  "source": "/backup/snapshot.yaml",
  "dry_run": true
}
```
Expected:** 200 OK, restore plan previewed
AI Coder Impact:** ⭐⭐⭐⭐ - Safe preview before restore

### 11.5: Invalid source format (error)
**Purpose:** Error handling
Input:```json
{
  "source": "/backup/invalid.dat"
}
```
Expected:** 400 Bad Request, invalid format
AI Coder Impact:** ⭐⭐ - Clear error message

---

## Tool 12: repo_git (5 parameters)

### Scenario 12.1: Git log with limit
**Purpose:** View commit history
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "subcommand": "log",
  "args": ["--oneline", "-n", "5"]
}
```
Expected:** 200 OK, last 5 commits returned
AI Coder Impact:** ⭐⭐⭐⭐ - Commit history awareness

### Scenario 12.2: Git status
**Purpose:** Check working tree
**Input:```json
{
  "repo_path": "/invalid/path",
  "subcommand": "status"
}
```
Expected:** 200 OK, working tree status returned
AI Coder Impact:** ⭐⭐⭐⭐ - Working tree awareness

### Scenario 12.3: Git branch list
**Purpose:** List branches
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "subcommand": "branch",
  "args": ["-a"]
}
```
Expected:** 200 OK, all branches listed
AI Coder Impact:** ⭐⭐⭐ - Branch awareness

### Scenario 12.4: Git diff (latest commit)
**Purpose:** View changes
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "subcommand": "diff",
  "args": ["HEAD~1"]
}
```
Expected:** 200 OK, diff returned
AI Coder Impact:** ⭐⭐⭐⭐ - Change awareness

### Scenario 12.5: Dry-run (undocumented feature)
**Purpose:** Preview git command
**Input:```json
{
  "repo_path": "/tmp/test-repo",
  "subcommand": "reset",
  "args": ["--hard"],
  "dry_run": true
}
```
Expected:** 200 OK, command previewed but not executed
AI Coder Impact:** ⭐⭐⭐⭐ - Safe preview before destructive git commands

---

## Tool 13: repo_svn (5 parameters)

### Scenario 13.1: SVN info
**Purpose:** Get SVN metadata
**Input:```json
{
  "target": "/tmp/test-repo",
  "subcommand": "info"
}
```
Expected:** 200 OK, SVN info returned
AI Coder Impact:** ⭐⭐⭐ - SVN awareness

### Scenario 13.2: SVN status
**Purpose:** Check SVN status
**Input:```json
{
  "target": "/tmp/test-repo",
  "subcommand": "status"
}
```
Expected:** 200 OK, SVN status returned
AI Coder Impact:** ⭐⭐⭐ - SVN status awareness

### Scenario 13.3: SVN update
**Purpose:** Update working copy
Input:```json
{
  "target": "/tmp/test-repo",
  "subcommand": "update"
}
```
Expected:** 200 OK, working copy updated
AI Coder Impact:** ⭐⭐⭐ - SVN update awareness

### Scenario 13.4: SVN commit
**Purpose:** Commit changes
Input:```json
{
  "target": "/tmp/test-repo",
  "subcommand: "commit",
  "args": ["-m", "Fixed bug"]
}
```
Expected:** 200 OK, commit executed
AI Coder Impact:** ⭐⭐⭐ - SVN commit awareness

### Scenario 13.5: Dry-run (undocumented feature)
**Purpose:** Preview SVN command
Input:```json
{
  "target": "/tmp/test-repo",
  subcommand: "update",
  "dry_run: true
}
```
Expected:** 200 OK, command previewed but not executed
AI Coder Impact:** ⭐⭐⭐⭐ - Safe preview before destructive SVN commands

---

## Test Execution Plan

### Phase 1: Smoke Tests (Critical Path)
- Execute 1-2 scenarios per tool (happy path + 1 error)
- Focus on most common use cases
- Verify error handling works correctly

### Phase 2: Comprehensive Testing
- Execute all scenarios systematically
- Document results, failures, and edge cases
- Test undocumented features where applicable

### Phase 3: Integration Testing
- Test cross-tool workflows (init → inspect → analyze → sync)
- Test VCS integration (git operations, git history)
- Test database operations (compact, cleanup, dump, restore)

### Phase 4: Performance Testing
- Test with large repositories
- Test with deep directory structures
- Test with concurrent operations

---

## Success Criteria

- **Pass Rate:** >95% of scenarios pass
- **Error Handling:** All error scenarios return appropriate error codes and messages
- **Performance:** Operations complete within acceptable time limits
- **Data Integrity:** No data corruption during operations
- **Security:** Path traversal, SSRF, and other security guards function correctly

---

*This test plan follows Aegis Codeworks QA standards and focuses on repository domain as requested.*
