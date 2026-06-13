# CodeCortex QA Test Plan

> **Date:** 2026-05-28
> **Scope:** MCP Server Tools + CLI Tools Multi-Scenario Testing
> **Tester:** QA Expert (Cascade)
> **Status:** In Progress

---

## Executive Summary

This document outlines comprehensive multi-scenario test cases for all CodeCortex MCP Server tools and CLI commands. Testing covers normal operations, edge cases, error handling, and integration scenarios.

---

## MCP Server Tools Test Scenarios

### Tool 1: `codecortex:repository` (13 actions)

#### Action: `init`
- **Scenario 1.1:** Initialize new Git repository with remote URL
- **Scenario 1.2:** Initialize existing repository (force re-init)
- **Scenario 1.3:** Initialize SVN repository
- **Scenario 1.4:** Initialize with custom scope (include/exclude patterns)
- **Scenario 1.5:** Initialize non-existent path (error handling)
- **Scenario 1.6:** Initialize with invalid remote URL (error handling)

#### Action: `inspect`
- **Scenario 2.1:** Inspect initialized repository
- **Scenario 2.2:** Inspect with git diagnostics enabled
- **Scenario 2.3:** Inspect with index metadata
- **Scenario 2.4:** Inspect non-existent repository (error handling)
- **Scenario 2.5:** Inspect with file stats

#### Action: `analyze`
- **Scenario 3.1:** Full analysis with default settings
- **Scenario 3.2:** Dry-run analysis (no re-indexing)
- **Scenario 3.3:** Analysis with custom max_depth
- **Scenario 3.4:** Analysis with code map generation
- **Scenario 3.5:** Analysis with incremental sync
- **Scenario 3.6:** Analysis on non-indexed repository

#### Action: `sync`
- **Scenario 4.1:** Auto sync mode
- **Scenario 4.2:** Dry-run sync preview
- **Scenario 4.3:** Sync with custom scope (include/exclude)
- **Scenario 4.4:** Sync with reindex_updated=true
- **Scenario 4.5:** Sync with remove_deleted=true
- **Scenario 4.6:** Sync non-existent repository (error handling)

#### Action: `audit`
- **Scenario 5.1:** Full security audit (secrets, PII, misconfig)
- **Scenario 5.2:** Audit with custom exclude patterns
- **Scenario 5.3:** Audit with git history scan
- **Scenario 5.4:** Audit on empty repository
- **Scenario 5.5:** Audit with specific categories only

#### Action: `staleness`
- **Scenario 6.1:** Check staleness vs remote
- **Scenario 6.2:** Check with local changes included
- **Scenario 6.3:** Check with remote fetch
- **Scenario 6.4:** Check non-existent repository (error handling)

#### Action: `list`
- **Scenario 7.1:** List all repositories (default)
- **Scenario 7.2:** List with status filter (active/archived)
- **Scenario 7.3:** List with pagination (limit/offset)
- **Scenario 7.4:** List with custom ordering
- **Scenario 7.5:** List empty database

#### Action: `compact`
- **Scenario 8.1:** Compact database with VACUUM
- **Scenario 8.2:** Compact with YAML export
- **Scenario 8.3:** Dry-run compact
- **Scenario 8.4:** Compact with custom output path

#### Action: `cleanup`
- **Scenario 9.1:** Cleanup repository data
- **Scenario 9.2:** Cleanup with snapshot deletion
- **Scenario 9.3:** Dry-run cleanup
- **Scenario 9.4:** Force cleanup
- **Scenario 9.5:** Cleanup non-existent repo_id (error handling)

#### Action: `dump`
- **Scenario 10.1:** Export all data to YAML
- **Scenario 10.2:** Export with custom output directory
- **Scenario 10.3:** Export with findings included
- **Scenario 10.4:** Dry-run dump
- **Scenario 10.5:** Export to JSON format

#### Action: `restore`
- **Scenario 11.1:** Restore from dump file
- **Scenario 11.2:** Restore with overwrite
- **Scenario 11.3:** Restore with checksum verification
- **Scenario 11.4:** Restore from snapshot directory
- **Scenario 11.5:** Restore invalid dump file (error handling)

#### Action: `git`
- **Scenario 12.1:** Git log with limit
- **Scenario 12.2:** Git diff (latest commit)
- **Scenario 12.3:** Git branches list
- **Scenario 12.4:** Git custom subcommand
- **Scenario 12.5:** Git on non-Git repository (error handling)

#### Action: `svn`
- **Scenario 13.1:** SVN info retrieval
- **Scenario 13.2:** SVN custom subcommand
- **Scenario 13.3:** SVN on non-SVN repository (error handling)

---

### Tool 2: `codecortex:filesystem` (12 actions)

#### Action: `read`
- **Scenario 1.1:** Read text file with UTF-8 encoding
- **Scenario 1.2:** Read with offset and limit
- **Scenario 1.3:** Read binary file
- **Scenario 1.4:** Read non-existent file (error handling)
- **Scenario 1.5:** Read with custom encoding

#### Action: `write`
- **Scenario 2.1:** Write new file (create mode)
- **Scenario 2.2:** Overwrite existing file
- **Scenario 2.3:** Append to file
- **Scenario 2.4:** Write with parent directory creation
- **Scenario 2.5:** Write with backup
- **Scenario 2.6:** Write with atomic operation
- **Scenario 2.7:** Write to read-only path (error handling)

#### Action: `delete`
- **Scenario 3.1:** Delete single file
- **Scenario 3.2:** Delete directory (recursive)
- **Scenario 3.3:** Delete with force flag
- **Scenario 3.4:** Dry-run delete
- **Scenario 3.5:** Delete non-existent path (error handling)

#### Action: `copy`
- **Scenario 4.1:** Copy file
- **Scenario 4.2:** Copy directory
- **Scenario 4.3:** Copy with overwrite
- **Scenario 4.4:** Copy with destination parent creation
- **Scenario 4.5:** Copy to existing destination without overwrite (error handling)
- **Scenario 4.6:** Copy non-existent source (error handling)

#### Action: `move`
- **Scenario 5.1:** Move file
- **Scenario 5.2:** Move directory
- **Scenario 5.3:** Move with overwrite
- **Scenario 5.4:** Move with destination parent creation
- **Scenario 5.5:** Move to existing destination without overwrite (error handling)
- **Scenario 5.6:** Move non-existent source (error handling)

#### Action: `mkdir`
- **Scenario 6.1:** Create single directory
- **Scenario 6.2:** Create with parent directories
- **Scenario 6.3:** Create existing directory (error handling)
- **Scenario 6.4:** Dry-run mkdir

#### Action: `list` (ls)
- **Scenario 7.1:** List directory contents (non-recursive)
- **Scenario 7.2:** List with recursion
- **Scenario 7.3:** List with max depth
- **Scenario 7.4:** List with file pattern filter
- **Scenario 7.5:** List including hidden files
- **Scenario 7.6:** List non-existent directory (error handling)

#### Action: `search`
- **Scenario 8.1:** Search by filename pattern
- **Scenario 8.2:** Search by content regex
- **Scenario 8.3:** Search with both filename and content
- **Scenario 8.4:** Search with max depth limit
- **Scenario 8.5:** Search with max results limit
- **Scenario 8.6:** Search with exclude patterns
- **Scenario 8.7:** Search with replace text (dry-run)
- **Scenario 8.8:** Search non-existent root (error handling)

#### Action: `watch`
- **Scenario 9.1:** Watch directory for changes (default interval)
- **Scenario 9.2:** Watch with custom poll interval
- **Scenario 9.3:** Watch with max events limit
- **Scenario 9.4:** Watch non-recursive
- **Scenario 9.5:** Watch file instead of directory (error handling)

#### Action: `usage`
- **Scenario 10.1:** Analyze disk usage for directory
- **Scenario 10.2:** Analyze disk usage for file
- **Scenario 10.3:** Usage with depth limit
- **Scenario 10.4:** Usage with aggregation by file
- **Scenario 10.5:** Usage with max items limit
- **Scenario 10.6:** Usage non-existent path (error handling)

#### Action: `audit`
- **Scenario 11.1:** File permissions audit
- **Scenario 11.2:** Security audit with severity filter
- **Scenario 11.3:** Audit with max file size limit
- **Scenario 11.4:** Audit with result limit
- **Scenario 11.5:** Audit non-existent path (error handling)

---

### Tool 3: `codecortex:codebase` (8 actions)

#### Action: `analyze`
- **Scenario 1.1:** Analyze single file
- **Scenario 1.2:** Analyze directory
- **Scenario 1.3:** Analyze with custom max_depth
- **Scenario 1.4:** Analyze with focus parameter
- **Scenario 1.5:** Analyze with follow_depth
- **Scenario 1.6:** Analyze with cursor (pagination)
- **Scenario 1.7:** Analyze without docstrings
- **Scenario 1.8:** Analyze with comments included
- **Scenario 1.9:** Analyze non-existent target (error handling)

#### Action: `search`
- **Scenario 2.1:** Text search (FTS)
- **Scenario 2.2:** Semantic search
- **Scenario 2.3:** Graph-enriched search
- **Scenario 2.4:** Search with symbol type filter
- **Scenario 2.5:** Search with file pattern
- **Scenario 2.6:** Search with limit
- **Scenario 2.7:** Search empty query (error handling)

#### Action: `audit`
- **Scenario 3.1:** Standards compliance audit
- **Scenario 3.2:** Audit with custom categories
- **Scenario 3.3:** Audit with severity threshold
- **Scenario 3.4:** Audit with entropy threshold
- **Scenario 3.5:** Audit with max file size
- **Scenario 3.6:** Audit with specific files list
- **Scenario 3.7:** Audit with AST enabled
- **Scenario 3.8:** Audit with .aiignore
- **Scenario 3.9:** Audit with since timestamp

#### Action: `graph` (sub-actions)
- **Scenario 4.1:** Build graph (sub_action: build)
- **Scenario 4.2:** Query graph - callers (sub_action: query)
- **Scenario 4.3:** Query graph - callees
- **Scenario 4.4:** Query graph - path
- **Scenario 4.5:** Query graph - ancestors
- **Scenario 4.6:** Query graph - descendants
- **Scenario 4.7:** Query graph - trace_flow
- **Scenario 4.8:** Query graph - trace_path
- **Scenario 4.9:** Graph audit (sub_action: audit)
- **Scenario 4.10:** Relationships query (sub_action: relationships)
- **Scenario 4.11:** Graph operations on non-indexed repo (error handling)

#### Action: `status`
- **Scenario 5.1:** Get codebase metrics snapshot
- **Scenario 5.2:** Status with metrics included
- **Scenario 5.3:** Status with VCS info
- **Scenario 5.4:** Status with symbols
- **Scenario 5.5:** Status with language filter

#### Action: `index` (sub-actions)
- **Scenario 6.1:** Build index (sub_action: build)
- **Scenario 6.2:** Rebuild index (sub_action: rebuild)
- **Scenario 6.3:** Remove index (sub_action: remove)
- **Scenario 6.4:** Index status (sub_action: status)
- **Scenario 6.5:** Index with specific files
- **Scenario 6.6:** Index operations on non-existent repo (error handling)

#### Action: `test` (sub-actions)
- **Scenario 7.1:** Run tests (sub_action: run)
- **Scenario 7.2:** Discover tests (sub_action: discover)
- **Scenario 7.3:** Diagnose failures (sub_action: diagnose)
- **Scenario 7.4:** Generate tests (sub_action: generate)
- **Scenario 7.5:** Test with custom framework
- **Scenario 7.6:** Test with filter
- **Scenario 7.7:** Test with specific test names
- **Scenario 7.8:** Test with categories
- **Scenario 7.9:** Test with coverage format
- **Scenario 7.10:** Test with max duration
- **Scenario 7.11:** Test in async mode

#### Action: `refactor` (sub-actions)
- **Scenario 8.1:** Impact analysis (sub_action: impact)
- **Scenario 8.2:** Rename symbol (sub_action: rename)
- **Scenario 8.3:** Move code element (sub_action: move)
- **Scenario 8.4:** Extract function (sub_action: extract)
- **Scenario 8.5:** Inline function (sub_action: inline)
- **Scenario 8.6:** Change signature (sub_action: signature)
- **Scenario 8.7:** Refactor with dry-run
- **Scenario 8.8:** Refactor non-existent symbol (error handling)

---

### Tool 4: `codecortex:scaffolder` (7 actions)

#### Action: `list_stacks`
- **Scenario 1.1:** List all available stacks
- **Scenario 1.2:** List with filter (if supported)

#### Action: `get_stack`
- **Scenario 2.1:** Get detailed stack info
- **Scenario 2.2:** Get non-existent stack (error handling)

#### Action: `validate_name`
- **Scenario 3.1:** Validate valid project name
- **Scenario 3.2:** Validate invalid name (special chars)
- **Scenario 3.3:** Validate empty name (error handling)
- **Scenario 3.4:** Validate name with spaces

#### Action: `list_licenses`
- **Scenario 4.1:** List all available licenses

#### Action: `generate_content`
- **Scenario 5.1:** Generate .gitignore
- **Scenario 5.2:** Generate .env.example
- **Scenario 5.3:** Generate pyproject.toml
- **Scenario 5.4:** Generate README.md
- **Scenario 5.5:** Generate requirements.txt
- **Scenario 5.6:** Generate Dockerfile
- **Scenario 5.7:** Generate docker-compose.yml
- **Scenario 5.8:** Generate setup.sh
- **Scenario 5.9:** Generate setup.bat
- **Scenario 5.10:** Generate setup.ps1
- **Scenario 5.11:** Generate logger.py
- **Scenario 5.12:** Generate .author file
- **Scenario 5.13:** Generate .aiignore
- **Scenario 5.14:** Generate with custom project category
- **Scenario 5.15:** Generate with custom author/email
- **Scenario 5.16:** Generate invalid file_type (error handling)

#### Action: `generate_class`
- **Scenario 6.1:** Generate interface class
- **Scenario 6.2:** Generate abstract class
- **Scenario 6.3:** Generate model class
- **Scenario 6.4:** Generate repository class
- **Scenario 6.5:** Generate controller class
- **Scenario 6.6:** Generate service class
- **Scenario 6.7:** Generate value object
- **Scenario 6.8:** Generate DTO
- **Scenario 6.9:** Generate event class
- **Scenario 6.10:** Generate listener class
- **Scenario 6.11:** Generate job class
- **Scenario 6.12:** Generate middleware class
- **Scenario 6.13:** Generate factory class
- **Scenario 6.14:** Generate seeder class
- **Scenario 6.15:** Generate migration class
- **Scenario 6.16:** Generate enum class
- **Scenario 6.17:** Generate trait class
- **Scenario 6.18:** Generate helper class
- **Scenario 6.19:** Generate validator class
- **Scenario 6.20:** Generate mapper class
- **Scenario 6.21:** Generate with custom stack
- **Scenario 6.22:** Generate with custom module
- **Scenario 6.23:** Generate with overwrite
- **Scenario 6.24:** Generate invalid type (error handling)

#### Action: `create_project`
- **Scenario 7.1:** Create project with dry-run (default)
- **Scenario 7.2:** Create project with actual execution
- **Scenario 7.3:** Create with custom stack
- **Scenario 7.4:** Create with custom project type
- **Scenario 7.5:** Create with custom target path
- **Scenario 7.6:** Create with custom author/email
- **Scenario 7.7:** Create with custom version
- **Scenario 7.8:** Create with custom license
- **Scenario 7.9:** Create with overwrite
- **Scenario 7.10:** Create with AI configuration
- **Scenario 7.11:** Create with trainer files
- **Scenario 7.12:** Create with project code
- **Scenario 7.13:** Create project that already exists (error handling)
- **Scenario 7.14:** Create with invalid version (error handling)
- **Scenario 7.15:** Create with invalid name (error handling)

---

## CLI Tools Test Scenarios

### Domain: `repository` / `repo` (15 commands)

#### Command: `init`
- **Scenario 1.1:** Initialize new repository
- **Scenario 1.2:** Initialize with force flag
- **Scenario 1.3:** Initialize with custom VCS type (git/svn)
- **Scenario 1.4:** Initialize with remote URL
- **Scenario 1.5:** Initialize non-existent path (error handling)

#### Command: `inspect`
- **Scenario 2.1:** Inspect repository
- **Scenario 2.2:** Inspect non-existent path (error handling)

#### Command: `analyze`
- **Scenario 3.1:** Analyze repository
- **Scenario 3.2:** Analyze with dry-run
- **Scenario 3.3:** Analyze with max_depth
- **Scenario 3.4:** Analyze with codemap

#### Command: `sync`
- **Scenario 4.1:** Sync repository
- **Scenario 4.2:** Sync with dry-run
- **Scenario 4.3:** Sync non-existent repository (error handling)

#### Command: `audit`
- **Scenario 5.1:** Audit repository
- **Scenario 5.2:** Audit with exclude patterns
- **Scenario 5.3:** Audit non-existent path (error handling)

#### Command: `staleness`
- **Scenario 6.1:** Check staleness
- **Scenario 6.2:** Check non-existent repository (error handling)

#### Command: `list`
- **Scenario 7.1:** List all repositories
- **Scenario 7.2:** List empty database

#### Command: `compact`
- **Scenario 8.1:** Compact database

#### Command: `cleanup`
- **Scenario 9.1:** Cleanup project
- **Scenario 9.2:** Cleanup with repo_id
- **Scenario 9.3:** Cleanup non-existent repo_id (error handling)

#### Command: `dump`
- **Scenario 10.1:** Dump project data
- **Scenario 10.2:** Dump with custom output directory
- **Scenario 10.3:** Dump with repo_id

#### Command: `restore`
- **Scenario 11.1:** Restore from dump file
- **Scenario 11.2:** Restore non-existent file (error handling)

#### Command: `git`
- **Scenario 12.1:** Git log
- **Scenario 12.2:** Git diff
- **Scenario 12.3:** Git branches
- **Scenario 12.4:** Git with limit
- **Scenario 12.5:** Git on non-Git repo (error handling)

#### Command: `svn`
- **Scenario 13.1:** SVN info
- **Scenario 13.2:** SVN with invalid URL (error handling)

#### Command: `link`
- **Scenario 14.1:** Link repository with remote URL
- **Scenario 14.2:** Link non-existent repository (error handling)
- **Scenario 14.3:** Link already linked repository

#### Command: `deduplicate`
- **Scenario 15.1:** Detect duplicates (dry-run)
- **Scenario 15.2:** Apply deduplication
- **Scenario 15.3:** Deduplicate empty database

---

### Domain: `filesystem` / `fs` (13 commands)

#### Command: `read`
- **Scenario 1.1:** Read file
- **Scenario 1.2:** Read non-existent file (error handling)

#### Command: `write`
- **Scenario 2.1:** Write file
- **Scenario 2.2:** Write with mode (create/overwrite/append)
- **Scenario 2.3:** Write with encoding

#### Command: `delete`
- **Scenario 3.1:** Delete file
- **Scenario 3.2:** Delete with recursive
- **Scenario 3.3:** Delete with force
- **Scenario 3.4:** Delete non-existent path (error handling)

#### Command: `copy`
- **Scenario 4.1:** Copy file
- **Scenario 4.2:** Copy with overwrite
- **Scenario 4.3:** Copy non-existent source (error handling)

#### Command: `move`
- **Scenario 5.1:** Move file
- **Scenario 5.2:** Move with overwrite
- **Scenario 5.3:** Move non-existent source (error handling)

#### Command: `mkdir`
- **Scenario 6.1:** Create directory
- **Scenario 6.2:** Create with parents
- **Scenario 6.3:** Create existing directory (error handling)

#### Command: `list`
- **Scenario 7.1:** List directory
- **Scenario 7.2:** List with recursive
- **Scenario 7.3:** List with pattern
- **Scenario 7.4:** List non-existent path (error handling)

#### Command: `search`
- **Scenario 8.1:** Search files
- **Scenario 8.2:** Search with pattern
- **Scenario 8.3:** Search with content
- **Scenario 8.4:** Search with max-depth
- **Scenario 8.5:** Search with max-results
- **Scenario 8.6:** Search with hidden files

#### Command: `watch`
- **Scenario 9.1:** Watch directory
- **Scenario 9.2:** Watch with interval
- **Scenario 9.3:** Watch with max-events
- **Scenario 9.4:** Watch non-recursive
- **Scenario 9.5:** Watch non-directory (error handling)

#### Command: `tree`
- **Scenario 10.1:** Show tree
- **Scenario 10.2:** Tree with max-depth
- **Scenario 10.3:** Tree with exclude pattern

#### Command: `usage`
- **Scenario 11.1:** Analyze usage
- **Scenario 11.2:** Usage non-existent path (error handling)

#### Command: `audit`
- **Scenario 12.1:** Filesystem audit
- **Scenario 12.2:** Audit non-existent path (error handling)

---

### Domain: `codebase` / `cb` (8 commands)

#### Command: `analyze`
- **Scenario 1.1:** Analyze target
- **Scenario 1.2:** Analyze with mode
- **Scenario 1.3:** Analyze with max-depth
- **Scenario 1.4:** Analyze with focus
- **Scenario 1.5:** Analyze with follow-depth
- **Scenario 1.6:** Analyze with cursor

#### Command: `search`
- **Scenario 2.1:** Search query
- **Scenario 2.2:** Search with target
- **Scenario 2.3:** Search empty query (error handling)

#### Command: `audit`
- **Scenario 3.1:** Audit target
- **Scenario 3.2:** Audit with mode
- **Scenario 3.3:** Audit with severity
- **Scenario 3.4:** Audit with max-size
- **Scenario 3.5:** Audit with files

#### Command: `graph`
- **Scenario 4.1:** Graph build
- **Scenario 4.2:** Graph query
- **Scenario 4.3:** Graph relationships
- **Scenario 4.4:** Graph audit
- **Scenario 4.5:** Graph with max-depth
- **Scenario 4.6:** Graph with query-node
- **Scenario 4.7:** Graph with target-node
- **Scenario 4.8:** Graph with direction
- **Scenario 4.9:** Graph non-existent repo (error handling)

#### Command: `index`
- **Scenario 5.1:** Index status
- **Scenario 5.2:** Index build
- **Scenario 5.3:** Index reindex
- **Scenario 5.4:** Index clear
- **Scenario 5.5:** Index remove
- **Scenario 5.6:** Index non-existent repo (error handling)

#### Command: `status`
- **Scenario 6.1:** Get status
- **Scenario 6.2:** Status with repo_id
- **Scenario 6.3:** Status non-existent repo_id (error handling)

#### Command: `test`
- **Scenario 7.1:** Run tests
- **Scenario 7.2:** Test with framework
- **Scenario 7.3:** Test non-existent path (error handling)

#### Command: `refactor`
- **Scenario 8.1:** Refactor target
- **Scenario 8.2:** Refactor with old-name
- **Scenario 8.3:** Refactor with new-name
- **Scenario 8.4:** Refactor with file
- **Scenario 8.5:** Refactor with symbol flag
- **Scenario 8.6:** Refactor non-existent repo_id (error handling)

---

### Domain: `scaffolder` / `sc` (7 commands)

#### Command: `list-stacks`
- **Scenario 1.1:** List stacks

#### Command: `get-stack`
- **Scenario 2.1:** Get stack
- **Scenario 2.2:** Get non-existent stack (error handling)

#### Command: `validate-name`
- **Scenario 3.1:** Validate name
- **Scenario 3.2:** Validate invalid name (error handling)

#### Command: `list-licenses`
- **Scenario 4.1:** List licenses

#### Command: `generate`
- **Scenario 5.1:** Generate file_type
- **Scenario 5.2:** Generate with category
- **Scenario 5.3:** Generate with project-name
- **Scenario 5.4:** Generate with author
- **Scenario 5.5:** Generate with email
- **Scenario 5.6:** Generate with license
- **Scenario 5.7:** Generate invalid file_type (error handling)

#### Command: `make`
- **Scenario 6.1:** Make class
- **Scenario 6.2:** Make with type_id
- **Scenario 6.3:** Make with name
- **Scenario 6.4:** Make with stack
- **Scenario 6.5:** Make with module
- **Scenario 6.6:** Make with project
- **Scenario 6.7:** Make with author
- **Scenario 6.8:** Make with target
- **Scenario 6.9:** Make with overwrite
- **Scenario 6.10:** Make invalid type (error handling)

#### Command: `create`
- **Scenario 7.1:** Create project (dry-run)
- **Scenario 7.2:** Create with no-dry-run
- **Scenario 7.3:** Create with stack
- **Scenario 7.4:** Create with project-type
- **Scenario 7.5:** Create with target
- **Scenario 7.6:** Create with author
- **Scenario 7.7:** Create with email
- **Scenario 7.8:** Create with version
- **Scenario 7.9:** Create with license
- **Scenario 7.10:** Create with overwrite
- **Scenario 7.11:** Create with include-ai
- **Scenario 7.12:** Create with include-trainer
- **Scenario 7.13:** Create with project-code
- **Scenario 7.14:** Create invalid name (error handling)
- **Scenario 7.15:** Create invalid version (error handling)

---

### Domain: `server` (3 commands)

#### Command: `status`
- **Scenario 1.1:** Check server status (running)
- **Scenario 1.2:** Check server status (not running)

#### Command: `start`
- **Scenario 2.1:** Start server with default port
- **Scenario 2.2:** Start server with custom port
- **Scenario 2.3:** Start server with custom host
- **Scenario 2.4:** Start server with expose
- **Scenario 2.5:** Start already running server

#### Command: `stop`
- **Scenario 3.1:** Stop server
- **Scenario 3.2:** Stop with custom port
- **Scenario 3.3:** Stop non-running server

---

### Domain: `cloud` (5 commands)

#### Command: `init`
- **Scenario 1.1:** Initialize cloud sync
- **Scenario 1.2:** Init with server URL

#### Command: `push`
- **Scenario 2.1:** Push data
- **Scenario 2.2:** Push with remote URL
- **Scenario 2.3:** Push with no server configured (error handling)

#### Command: `pull`
- **Scenario 3.1:** Pull data
- **Scenario 3.2:** Pull with since timestamp
- **Scenario 3.3:** Pull with no server configured (error handling)

#### Command: `sync`
- **Scenario 4.1:** Sync (push + pull)
- **Scenario 4.2:** Sync with remote URL

#### Command: `status`
- **Scenario 5.1:** Check cloud status
- **Scenario 5.2:** Status with remote URL

---

### Domain: `cct` (7 commands)

#### Command: `projects`
- **Scenario 1.1:** List CCT projects

#### Command: `project-add`
- **Scenario 2.1:** Add project
- **Scenario 2.2:** Add with display-name

#### Command: `project-status`
- **Scenario 3.1:** Get project status
- **Scenario 3.2:** Status with project_id

#### Command: `think-start`
- **Scenario 4.1:** Start thinking session
- **Scenario 4.2:** Think with profile
- **Scenario 4.3:** Think with project-id
- **Scenario 4.4:** Think with model
- **Scenario 4.5:** Think with code-context
- **Scenario 4.6:** Think with cct-url

#### Command: `analyze`
- **Scenario 5.1:** LLM analyze
- **Scenario 5.2:** Analyze with format
- **Scenario 5.3:** Analyze with project-id
- **Scenario 5.4:** Analyze with code-context
- **Scenario 5.5:** Analyze with repo-path
- **Scenario 5.6:** Analyze with cct-url

#### Command: `code-analyze`
- **Scenario 6.1:** Code analyze via CodeCortex
- **Scenario 6.2:** Analyze with repo-path
- **Scenario 6.3:** Analyze with project-id
- **Scenario 6.4:** Analyze with cct-url

#### Command: `code-search`
- **Scenario 7.1:** Code search via CodeCortex
- **Scenario 7.2:** Search with repo-path
- **Scenario 7.3:** Search with search-type
- **Scenario 7.4:** Search with limit
- **Scenario 7.5:** Search with project-id
- **Scenario 7.6:** Search with cct-url

---

### Domain: `ai` (1 command)

#### Command: `analyze`
- **Scenario 1.1:** AI analyze
- **Scenario 1.2:** Analyze with prompt
- **Scenario 1.3:** Analyze with code
- **Scenario 1.4:** Analyze with repo
- **Scenario 1.5:** Analyze with format
- **Scenario 1.6:** Analyze with project-id
- **Scenario 1.7:** Analyze with cct-url
- **Scenario 1.8:** Analyze without CCT server (error handling)

---

### Domain: `remote` (4 commands)

#### Command: `path-map`
- **Scenario 1.1:** Register path mapping
- **Scenario 1.2:** Map with device_path and server_path
- **Scenario 1.3:** Map with remote URL
- **Scenario 1.4:** Map without remote URL (error handling)

#### Command: `list`
- **Scenario 2.1:** List path mappings
- **Scenario 2.2:** List with remote URL
- **Scenario 2.3:** List without remote URL (error handling)

#### Command: `unmap`
- **Scenario 3.1:** Remove mapping
- **Scenario 3.2:** Unmap with mapping_id
- **Scenario 3.3:** Unmap with remote URL
- **Scenario 3.4:** Unmap without remote URL (error handling)

#### Command: `resolve`
- **Scenario 4.1:** Resolve device path
- **Scenario 4.2:** Resolve with device_path
- **Scenario 4.3:** Resolve with remote URL
- **Scenario 4.4:** Resolve without remote URL (error handling)

---

## Test Execution Strategy

### Phase 1: Smoke Tests (Critical Path)
- Execute 1-2 scenarios per tool/command to verify basic functionality
- Focus on happy paths and common error cases

### Phase 2: Comprehensive Testing
- Execute all scenarios systematically
- Document results, failures, and edge cases

### Phase 3: Integration Testing
- Test cross-tool interactions
- Test end-to-end workflows

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

*This test plan follows CODDY Codeworks QA standards.*
