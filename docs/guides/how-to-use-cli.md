# CodeCortex CLI — Complete Usage Guide

CodeCortex CLI provides a unified command-line interface for repository management, filesystem operations, codebase intelligence, project scaffolding, knowledge graphs, IDE memory harvesting, server lifecycle, cloud sync, and AI-powered analysis.

## Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--no-pretty` | flag | `false` | Disable pretty-printed JSON output (compact) |
| `--remote URL` | string | `$CODECORTEX_REMOTE` | Execute commands on a remote CodeCortex server |
| `--ai` | flag | `false` | Enrich output with AI insight via CCT Server |
| `--ai-format FMT` | string | `insight` | AI output format: `insight`, `summary`, `remediation`, `explain` |

## Built-in Commands

```
codecortex help     Show help message with all commands and examples
codecortex version  Show version, CLI version, and tool counts
```

---

## 1. Repository (`repository`, alias: `repo`)

Manage repository lifecycle: initialization, analysis, syncing, auditing, and cleanup.

### `repo init PATH`

Initialize a repository for analysis.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to the repository |
| `--vcs-type` | choice | `git` | Version control: `git`, `svn` |
| `--remote-url` | string | auto-detected | Remote origin URL |
| `--force` | flag | `false` | Re-initialize if already exists |

> Auto-detects `git remote origin.url` if `--remote-url` is not provided.

### `repo inspect PATH`

Retrieve repository metadata, file/symbol counts.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to repository |

### `repo analyze PATH`

Run the full analysis pipeline (sync → index → analyze).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to repository |
| `--dry-run` | flag | `false` | Analyze existing data without re-indexing |
| `--max-depth N` | int | unlimited | Max directory depth to traverse |
| `--codemap` | flag | `false` | Include symbol codemap |

### `repo sync PATH`

Sync repository with the filesystem (detect changes).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to repository |
| `--dry-run` | flag | `false` | Show what would sync without executing |

### `repo audit PATH`

Run a security audit (secret scanning).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to repository |

### `repo staleness PATH`

Check if re-indexing is needed.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to repository |

### `repo list`

List all registered repositories.

### `repo compact`

Vacuum/compact the database.

### `repo cleanup REPO_ID`

Permanently delete a project and its data.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `REPO_ID` | positional | required | Repository UUID |

### `repo dump REPO_ID`

Export project data to a dump file.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `REPO_ID` | positional | required | Repository UUID |
| `--output-dir DIR` | string | `database/exports` | Output directory |

### `repo restore FILE`

Import a project from a dump file.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `FILE` | positional | required | Path to dump file |

### `repo git PATH <action>`

Run Git operations against a repository.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to repository |
| `action` | choice | required | `log`, `diff`, `branches` |
| `--limit N` | int | `50` | Commit limit (log only) |

### `repo svn URL`

Retrieve SVN repository info.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `URL` | positional | required | SVN repository URL |

### `repo link PATH REMOTE_URL`

Associate a local repo path with a remote URL (cross-device identity).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Repository path |
| `REMOTE_URL` | positional | required | Git remote origin URL |

### `repo deduplicate`

Detect and merge duplicate repository entries in the database.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--apply` | flag | `false` | Apply merge (default is dry-run preview) |

---

## 2. Filesystem (`filesystem`, alias: `fs`)

Read, write, search, and manage files and directories.

### `fs read PATH`

Read a file or directory and return its content.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to file or directory |

### `fs write PATH CONTENT`

Write content to a file.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to file |
| `CONTENT` | positional | required | Content to write |
| `--mode MODE` | choice | `create` | Write mode: `create`, `overwrite`, `append` |
| `--encoding ENC` | choice | `utf8` | Content encoding: `utf8`, `base64` |

### `fs delete PATH`

Delete a file or directory.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to delete |
| `--recursive` | flag | `false` | Recursive delete (for directories) |
| `--force` | flag | `false` | Force delete (ignore errors) |

### `fs copy SRC DEST`

Copy a file or directory.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `SRC` | positional | required | Source path |
| `DEST` | positional | required | Destination path |
| `--overwrite` | flag | `false` | Overwrite destination if exists |

### `fs move SRC DEST`

Move (rename) a file or directory.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `SRC` | positional | required | Source path |
| `DEST` | positional | required | Destination path |
| `--overwrite` | flag | `false` | Overwrite destination if exists |

### `fs mkdir PATH`

Create a directory.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Directory path |
| `--parents` | flag | `false` | Create parent directories (like `mkdir -p`) |

### `fs search ROOT`

Search files by glob pattern and/or content regex.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `ROOT` | positional | required | Root path to search |
| `--pattern PAT` | string | — | File glob pattern (e.g. `*.py`) |
| `--content REGEX` | string | — | Content regex pattern |
| `--max-depth N` | int | unlimited | Max directory depth |
| `--max-results N` | int | `100` | Max results to return |
| `--no-recursive` | flag | `false` | Non-recursive search (top-level only) |
| `--hidden` | flag | `false` | Include hidden files |

### `fs list PATH`

List directory contents.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Directory path |
| `--recursive` | flag | `false` | Recursive listing |
| `--pattern PAT` | string | — | File glob pattern filter |

### `fs watch TARGET`

Poll a directory for filesystem changes.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `TARGET` | positional | required | Directory to watch |
| `--interval SEC` | float | `1.0` | Poll interval in seconds |
| `--max-events N` | int | `10` | Max events to collect before stopping |
| `--no-recursive` | flag | `true` (recursive) | Non-recursive watch |

### `fs tree PATH`

Show a directory tree with metadata.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to directory |
| `--max-depth N` | int | `6` | Maximum traversal depth |
| `--exclude PAT` | string | — | Exclude pattern (glob) |

### `fs usage PATH`

Analyze disk usage — total size, file/dir counts, largest files.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to analyze |

### `fs audit PATH`

Run a security audit on filesystem permissions.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Path to audit |

---

## 3. Codebase (`codebase`, alias: `cb`)

Code intelligence: analysis, semantic search, graph queries, auditing, testing, and refactoring.

### `cb analyze TARGET`

Analyze code structure and metadata.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `TARGET` | positional | required | File or directory path |
| `--mode MODE` | choice | `auto` | Analysis mode: `auto`, `full`, `quick` |
| `--max-depth N` | int | `3` | Max traversal depth |
| `--summary` | flag | `false` | Return summary only |
| `--focus SYMBOL` | string | — | Symbol to focus analysis on |
| `--follow-depth N` | int | `1` | Depth for call graph traversal |

### `cb search QUERY`

Semantic search across indexed code.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `QUERY` | positional | required | Search query (natural language) |
| `--target PATH` | string | — | Scope search to specific path |

### `cb audit TARGET`

Run a code audit for security or quality issues.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `TARGET` | positional | required | Target path |
| `--mode MODE` | choice | `auto` | Audit mode: `auto`, `security`, `quality` |

### `cb graph TARGET <action>`

Knowledge graph operations.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `TARGET` | positional | required | Repository path |
| `action` | choice | required | `build`, `query`, `relationships`, `audit` |
| `--max-depth N` | int | `3` | Max traversal depth |
| `--query-node NAME` | string | — | Node name for query action |
| `--target-node ID` | string | — | Node ID for relationships action |
| `--direction DIR` | choice | `outgoing` | Relationship direction: `incoming`, `outgoing`, `both` |

### `cb index TARGET <action>`

Index management.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `TARGET` | positional | required | Repository path |
| `action` | choice | required | `status`, `build`, `reindex`, `clear`, `remove` |

### `cb status REPO_ID`

Get repository indexing status.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `REPO_ID` | positional | required | Repository UUID |

### `cb test PATH`

Run tests via the integrated test runner.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PATH` | positional | required | Test path |
| `--framework NAME` | string | — | Test framework (e.g. pytest, unittest) |

### `cb refactor REPO_ID TARGET`

Refactor code (rename symbols, files).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `REPO_ID` | positional | required | Repository UUID |
| `TARGET` | positional | required | Target path or symbol |
| `--old-name NAME` | string | — | Old name to rename |
| `--new-name NAME` | string | — | New name |
| `--file PATH` | string | — | File path (for file refactoring) |
| `--symbol` | flag | `false` | Refactor a symbol (not a file) |

---

## 4. Scaffolder (`scaffolder`, alias: `sc`)

Project scaffolding: generate boilerplate, validate names, scaffold full projects.

### `sc list-stacks`

List all available technology stacks (Python, Rust, Go, TypeScript, etc.).

### `sc get-stack NAME`

Get detailed information about a specific stack.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `NAME` | positional | required | Stack name (e.g. `python`, `rust`, `go`) |

### `sc validate-name NAME`

Validate a project name (checks naming conventions).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `NAME` | positional | required | Name to validate |

### `sc list-licenses`

List available license types.

### `sc generate FILE_TYPE`

Generate boilerplate file content (preview only, no file written).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `FILE_TYPE` | positional | required | File type: `gitignore`, `env`, `pyproject`, `readme`, `requirements`, `dockerfile`, `docker_compose`, `setup_sh`, `setup_bat`, `setup_ps1`, `logger_py`, `author_file`, `ai_ignore` |
| `--category CAT` | string | `standard` | Project category: `standard`, `data_science`, `web_api`, `cli_tool`, `automation`, `custom` |
| `--project-name NAME` | string | `My Project` | Project name |
| `--author NAME` | string | `Author` | Author name |
| `--email EMAIL` | string | `author@example.com` | Author email |
| `--license LICENSE` | string | `MIT` | License name |

### `sc make TYPE_ID NAME`

Generate a class/entity file.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `TYPE_ID` | positional | required | Class type (e.g. `entity`, `repository`, `service`, `controller`) |
| `NAME` | positional | required | Class name |
| `--stack NAME` | string | `python` | Technology stack |
| `--module NAME` | string | — | Module name |
| `--project NAME` | string | `Project` | Project name |
| `--author NAME` | string | `Author` | Author name |
| `--target PATH` | string | — | Target output path |
| `--overwrite` | flag | `false` | Overwrite existing file |

### `sc create NAME`

Scaffold a full project from a template.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `NAME` | positional | required | Project name |
| `--stack NAME` | string | `python` | Technology stack |
| `--project-type TYPE` | string | `standard` | Project type (stack-dependent) |
| `--target PATH` | string | default output dir | Target output directory |
| `--author NAME` | string | `Author` | Author name |
| `--email EMAIL` | string | `author@example.com` | Author email |
| `--version VER` | string | `0.1.0` | Project version |
| `--license LICENSE` | string | `MIT` | License |
| `--dry-run` | flag | `true` | Preview only (default) |
| `--no-dry-run` | flag | `false` | Execute scaffolding (override dry-run) |
| `--overwrite` | flag | `false` | Overwrite existing project directory |
| `--include-ai` | flag | `false` | Include AI configuration (.aiignore) |
| `--include-trainer` | flag | `false` | Include trainer files |
| `--project-code CODE` | string | — | Project code prefix |

---

## 5. Knowledge Graph (`knowledge`, alias: `kg`)

Extract, query, and explore engineering knowledge from documentation.

### `kg extract REPO_PATH`

Extract knowledge chunks from documentation files.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `REPO_PATH` | positional | required | Repository path to scan |
| `--types [TYPE ...]` | string[] | — | Knowledge types to extract (space-separated) |

### `kg query TASK`

Query knowledge relevant to a task.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `TASK` | positional | required | Natural language task description |
| `--types [TYPE ...]` | string[] | — | Filter by knowledge types |
| `--min-importance SCORE` | float | `0.0` | Minimum importance score |
| `--limit N` | int | `20` | Max results |

### `kg status`

Show knowledge extraction coverage (total chunks, by type, sources).

### `kg relationships`

Get knowledge graph relationships.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--focus TOPIC` | string | — | Focus on specific topic |

---

## 6. IDE Graph (`idegraph`, alias: `ig`)

Cross-IDE memory harvesting and workspace intelligence.

### `ig search QUERY`

Search IDE memories.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `QUERY` | positional | required | Search keyword |
| `--project NAME` | string | — | Filter by project name |
| `--ide NAME` | string | — | Filter by IDE name |
| `--limit N` | int | `10` | Max results |

### `ig get ID`

Get a specific memory by ID.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `ID` | positional | required | Memory ID |

### `ig list`

List IDE memories with filters.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--project NAME` | string | — | Filter by project name |
| `--workspace-key KEY` | string | — | Filter by workspace key |
| `--ide NAME` | string | — | Filter by IDE name |
| `--limit N` | int | `20` | Max results |
| `--offset N` | int | `0` | Result offset |

### `ig ingest`

Run all IDE parsers to harvest memories.

### `ig refresh PROJECT_PATH`

Re-ingest a specific project path.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PROJECT_PATH` | positional | required | Project path to refresh |
| `--force` | flag | `false` | Force re-ingestion |

### `ig health`

Check database health status.

### `ig stats`

Show ingestion statistics.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--ide NAME` | string | — | Filter by IDE name |
| `--since ISO` | string | — | ISO timestamp filter |

### `ig compact`

Compact conversations via LLM (summarize long sessions).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--limit N` | int | `5` | Number of conversations to compact |

### `ig workspace WORKSPACE_KEY`

Get workspace details by key.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `WORKSPACE_KEY` | positional | required | Workspace key hash |

### `ig harvest`

Harvest IDE configs and artifacts from all detected IDEs.

---

## 7. Server

Manage the CodeCortex HTTP server lifecycle.

### `server status`

Check if the HTTP server is running.

### `server start`

Start the HTTP server.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--port N` | int | `8001` | Server port |
| `--host HOST` | string | `127.0.0.1` | Bind host |
| `--expose URL` | string | — | Relay URL to expose via tunnel (e.g. `https://api.codecortex.ai`) |

### `server stop`

Stop the running HTTP server.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--port N` | int | `8001` | Server port to stop |

---

## 8. Cloud Sync

Git-style push/pull for portable project data.

### `cloud init SERVER_URL`

Initialize cloud sync configuration.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `SERVER_URL` | positional | required | Server URL (e.g. `http://server:8001`) |

### `cloud push`

Upload local portable data to the configured server.

### `cloud pull`

Download remote data from the server.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--since ISO` | string | last pull | ISO timestamp to pull from |

### `cloud sync`

Push then pull (bi-directional sync).

### `cloud status`

Show cloud sync status (device, server, last push/pull times).

---

## 9. CCT (Creative Critical Thinking)

Proxy commands to the CCT Server for cognitive computing and LLM-powered analysis.

> All `cct` subcommands support `--cct-url URL` to override the CCT server URL.

### `cct projects`

List all registered CCT projects.

### `cct project-add PROJECT_ID`

Register a new CCT project.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PROJECT_ID` | positional | required | Project ID |
| `--display-name NAME` | string | — | Display name |

### `cct project-status PROJECT_ID`

Get project health and status.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PROJECT_ID` | positional | required | Project ID |

### `cct think-start PROBLEM`

Start a structured thinking session.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PROBLEM` | positional | required | Problem statement |
| `--profile PROFILE` | string | `balanced` | Thinking profile: `balanced`, `creative`, `critical`, `mimic_user` |
| `--project-id ID` | string | `default` | Project ID |
| `--model MODEL` | string | — | LLM model ID (empty = default) |
| `--code-context CODE` | string | — | Optional code snippet for context |
| `--cct-url URL` | string | — | CCT server URL override |

### `cct analyze PROMPT`

Lightweight LLM analysis.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `PROMPT` | positional | required | Analysis prompt |
| `--format FMT` | choice | `insight` | Output format: `insight`, `summary`, `remediation`, `explain`, `free` |
| `--project-id ID` | string | `default` | Project ID |
| `--code-context CODE` | string | — | Optional code context |
| `--repo-path PATH` | string | — | Repository path for context |
| `--cct-url URL` | string | — | CCT server URL override |

### `cct code-analyze QUERY`

Analyze code via CodeCortex through CCT.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `QUERY` | positional | required | Code question or symbol |
| `--repo-path PATH` | string | `""` | Repository path |
| `--project-id ID` | string | `default` | Project ID |
| `--cct-url URL` | string | — | CCT server URL override |

### `cct code-search QUERY`

Search code via CodeCortex through CCT.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `QUERY` | positional | required | Search query |
| `--repo-path PATH` | string | `""` | Repository path |
| `--search-type TYPE` | choice | `code` | `code`, `symbols` |
| `--limit N` | int | `10` | Max results |
| `--project-id ID` | string | `default` | Project ID |
| `--cct-url URL` | string | — | CCT server URL override |

---

## 10. AI

Direct AI analysis via CCT Server (flat command, no subcommands).

```
codecortex ai QUERY [--prompt] [--code] [--repo] [--format] [--project-id] [--cct-url]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `QUERY` | positional | required | Query or code question to analyze |
| `--prompt TEXT` | string | auto-generated | Custom prompt |
| `--code CODE` | string | — | Optional code snippet to include |
| `--repo PATH` | string | — | Repository path for context |
| `--format FMT` | choice | `insight` | AI output format: `insight`, `summary`, `remediation`, `explain`, `free` |
| `--project-id ID` | string | `default` | Project ID |
| `--cct-url URL` | string | — | CCT server URL override |

> Requires a running CCT Server. Auto-discovers at `http://127.0.0.1:8001`, or set via `--cct-url` or `$CCT_URL`.

---

## 11. Remote

Remote server path mapping and execution.

> All `remote` subcommands accept `--remote URL` to specify the server URL (default from `$CODECORTEX_REMOTE`).

### `remote path-map DEVICE_PATH SERVER_PATH`

Register a device-to-server path mapping.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `DEVICE_PATH` | positional | required | Local path on this device |
| `SERVER_PATH` | positional | required | Corresponding path on the server |
| `--remote URL` | string | — | Server URL |

### `remote list`

List registered path mappings.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--remote URL` | string | — | Server URL |

### `remote unmap MAPPING_ID`

Remove a path mapping.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `MAPPING_ID` | positional | required | Mapping ID to remove |
| `--remote URL` | string | — | Server URL |

### `remote resolve DEVICE_PATH`

Resolve a device path to its server-side equivalent.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `DEVICE_PATH` | positional | required | Local path to resolve |
| `--remote URL` | string | — | Server URL |

---

## Quick Reference

### Most Common Commands

```bash
# Initialize and analyze a repository
codecortex repo init /path/to/project
codecortex repo analyze /path/to/project

# Filesystem operations
codecortex fs read /path/to/file.py
codecortex fs search /path --pattern "*.py" --content "class "
codecortex fs tree /path/to/project

# Code intelligence
codecortex cb search "database connection"
codecortex cb graph /path build
codecortex cb audit /path/to/file.py

# Scaffolding
codecortex sc list-stacks
codecortex sc make entity User --stack python
codecortex sc create MyProject --stack python --dry-run

# Knowledge graph
codecortex kg extract /path/to/project
codecortex kg query "how does authentication work"

# IDE memory
codecortex ig search "payment"
codecortex ig ingest

# Server
codecortex server status
codecortex server start --port 8001

# Cloud sync
codecortex cloud init http://server:8001
codecortex cloud push

# AI analysis
codecortex ai "explain the authentication flow" --repo /path/to/project

# Remote execution (proxy to server)
codecortex --remote http://server:8001 repo list
```

### Remote Execution

Any domain command can be proxied to a remote CodeCortex server:

```bash
codecortex --remote http://server:8001 repo list
codecortex --remote http://server:8001 fs read /path/to/file.py
```

Set the default remote via `$CODECORTEX_REMOTE` environment variable.

### AI Enrichment

Append `--ai` to any command to enrich the output with AI-generated insights:

```bash
codecortex --ai repo list
codecortex --ai --ai-format summary fs usage /path
```
