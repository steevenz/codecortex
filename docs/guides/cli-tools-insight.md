# CodeCortex CLI Tools Reference

> **Audience**: Developers and AI agents using CodeCortex via command line.
> **Entry**: `python -m src.cli` or `codecortex` (when installed)
> **Pattern**: All CLI commands output JSON `{success, status_code, message, data, meta}`

---

## CLI Domains Overview

CodeCortex CLI is organized into **11 command domains** mapping to the same 6 unified MCP tools.

| Domain | Alias | Commands | Maps to MCP Tool |
|--------|-------|----------|------------------|
| `repository` | `repo` | init, inspect, analyze, sync, audit, staleness, history, list, compact, cleanup, dump, restore, git, svn, link, deduplicate | `codecortex:repository` |
| `filesystem` | `fs` | read, write, delete, move, copy, search, list, watch, tree, usage, audit | `codecortex:filesystem` |
| `codebase` | `cb` | analyze, search, audit, graph, index, status, test, refactor | `codecortex:codebase` |
| `scaffolder` | `sc` | list-stacks, get-stack, validate-name, list-licenses, generate, make, create | `codecortex:scaffolder` |
| `knowledge` | `kg` | extract, query, status, relationships, validate | `codecortex:knowledge` |
| `idegraph` | `ig` | search, get, list, ingest, refresh, health, stats, compact, workspace, harvest | `codecortex:idegraph` |
| `server` | — | status, start, stop | Server lifecycle |
| `cloud` | — | init, push, pull, sync, status | Cloud sync |
| `remote` | — | path-map, list, unmap, resolve | Remote path mapping |
| `cct` | — | think-start, analyze, projects, project-add, project-status, code-analyze, code-search | CCT proxy |
| `ai` | — | (query) | Direct AI analysis |

---

## `repository` — Repository Lifecycle

| Command | Args | Description |
|---------|------|-------------|
| `init <path>` | `--vcs-type`, `--remote-url`, `--force` | Initialize and index a repository |
| `inspect <path>` | — | Fast metadata check (zero parsing) |
| `analyze <path>` | `--dry-run`, `--max-depth`, `--codemap` | Full 7-phase analysis pipeline |
| `sync <path>` | `--dry-run` | Incremental re-index changed files |
| `audit <path>` | — | Security audit (secrets, PII, misconfig) |
| `staleness <path>` | — | Check if index is stale vs filesystem |
| `history <path>` | `--limit`, `--author` | Commit history and author stats |
| `list` | — | List all registered repositories |
| `compact` | — | VACUUM database maintenance |
| `cleanup <repo_id>` | — | **Destructive** — delete all repo data |
| `dump <repo_id>` | `--output-dir` | Export portable data dump |
| `restore <file>` | — | Import from dump file |
| `git <path> <action>` | `log|diff|branches`, `--limit` | Git operations wrapper |
| `svn <url>` | — | SVN operations wrapper |
| `link <path> <remote_url>` | — | Cross-device identity linking |
| `deduplicate` | `--apply` | Merge duplicate repo entries |

---

## `filesystem` — Secure File Operations

| Command | Args | Description |
|---------|------|-------------|
| `read <path>` | `--encoding`, `--offset`, `--limit` | Read file contents |
| `write <path> <content>` | `--encoding`, `--append` | Write or append to file |
| `delete <path>` | `--recursive` | Delete file or directory |
| `move <src> <dest>` | — | Move/rename file or directory |
| `copy <src> <dest>` | — | Copy file or directory |
| `search <path> <query>` | `--regex`, `--replace`, `--apply` | Content search with optional replace |
| `list <path>` | `--recursive`, `--pattern`, `--hidden`, `--meta` | Directory listing |
| `watch <target>` | `--since`, `--format`, `--max-changes`, `--timeout` | VCS-aware change detection |
| `tree <path>` | `--max-depth`, `--exclude`, `--hidden` | Directory tree display |
| `usage <path>` | `--unit`, `--depth`, `--vcs`, `--aggregate-by` | Disk usage analysis |
| `audit <path>` | `--severity`, `--no-recursive`, `--max-file-size-mb` | Security audit (permissions, hidden files) |

---

## `codebase` — Code Intelligence

| Command | Args | Description |
|---------|------|-------------|
| `analyze <target>` | `--mode` (auto/full/quick), `--max-depth` | AST analysis and symbol extraction |
| `search <query>` | `--target` | Semantic code search |
| `audit <target>` | `--mode` (auto/security/quality) | Standards compliance audit |
| `graph <target> <action>` | `build/query/relationships/audit`, `--max-depth`, `--query-node`, `--target-node`, `--direction` | Knowledge graph operations |
| `index <target> <action>` | `status/build/reindex/clear/remove` | Index management |
| `status <repo_id>` | — | Repository status snapshot |
| `test <path>` | `--framework` | Run tests with auto-detection |
| `refactor <repo_id> <target>` | `--old-name`, `--new-name`, `--file`, `--symbol` | Safe semantic refactoring |

---

## `scaffolder` — Project Scaffolding

| Command | Args | Description |
|---------|------|-------------|
| `list-stacks` | — | List available technology stacks |
| `get-stack <name>` | — | Get stack details (conventions, project types) |
| `validate-name <name>` | — | Validate and normalize project name |
| `list-licenses` | — | List available license types |
| `generate <file_type>` | `--category`, `--project-name`, `--author`, `--email`, `--license` | Generate single file preview |
| `make <type_id> <name>` | `--stack`, `--module`, `--project`, `--target`, `--overwrite` | Generate class file |
| `create <name>` | `--stack`, `--project-type`, `--target`, `--dry-run` (default), `--overwrite`, `--include-ai`, `--include-trainer` | Full project scaffolding |

---

## `knowledge` — Engineering Knowledge

| Command | Args | Description |
|---------|------|-------------|
| `extract <repo_path>` | `--types`, `--repo-id` | Extract knowledge from documentation |
| `query [task]` | `--types`, `--min-importance`, `--max-importance`, `--min-confidence`, `--repo-id`, `--semantic`, `--fts-query`, `--regex`, `--glob`, `--limit` | Query knowledge graph |
| `status` | `--repo-id` | Knowledge extraction coverage |
| `relationships` | `--focus` | Explore knowledge relationships |
| `validate` | `--repo-id` | Validate code against extracted constraints |

---

## `idegraph` — Cross-IDE Memory

| Command | Args | Description |
|---------|------|-------------|
| `search <query>` | `--project`, `--ide`, `--limit`, `--search-mode`, `--search-fields`, `--date-from`, `--date-to`, `--min-messages`, `--max-messages` | Search memories across IDEs |
| `get <id>` | `--summary` | Get memory by ID |
| `list` | `--project`, `--workspace-key`, `--ide`, `--limit`, `--offset` | List memories |
| `ingest` | — | Run all IDE parsers |
| `refresh <project_path>` | `--force` | Re-ingest specific project |
| `health` | — | Check database health |
| `stats` | `--ide`, `--since` | Ingestion statistics |
| `compact` | `--limit` | Compact conversations via LLM |
| `workspace <workspace_key>` | — | Get workspace details |
| `harvest` | — | Harvest IDE configs and artifacts |

---

## `server` — Server Lifecycle

| Command | Args | Description |
|---------|------|-------------|
| `status` | — | Check HTTP server status |
| `start` | `--port` (8001), `--host` (127.0.0.1), `--expose` | Start HTTP server |
| `stop` | `--port` (8001) | Stop HTTP server |

---

## `cloud` — Cloud Sync

| Command | Args | Description |
|---------|------|-------------|
| `init <server_url>` | — | Initialize cloud sync |
| `push` | — | Upload local portable data to server |
| `pull` | `--since` | Download remote data from server |
| `sync` | — | Push then pull (bidirectional) |
| `status` | — | Show sync status |

---

## `remote` — Remote Path Mapping

| Command | Args | Description |
|---------|------|-------------|
| `path-map <device_path> <server_path>` | `--remote` | Register device-to-server path mapping |
| `list` | `--remote` | List path mappings |
| `unmap <mapping_id>` | `--remote` | Remove a path mapping |
| `resolve <device_path>` | `--remote` | Resolve device path to server path |

---

## `cct` — CCT Proxy

| Command | Args | Description |
|---------|------|-------------|
| `think-start <problem>` | `--profile`, `--project-id`, `--model`, `--code-context`, `--cct-url` | Start CCT thinking session |
| `analyze <prompt>` | `--format`, `--project-id`, `--code-context`, `--repo-path`, `--cct-url` | LLM analyze via CCT |
| `projects` | — | List CCT projects |
| `project-add <project_id>` | `--display-name` | Register CCT project |
| `project-status <project_id>` | — | Get project health |
| `code-analyze <query>` | `--repo-path`, `--project-id`, `--cct-url` | Analyze code via CodeCortex through CCT |
| `code-search <query>` | `--repo-path`, `--search-type`, `--limit`, `--project-id`, `--cct-url` | Search code via CodeCortex through CCT |

---

## `ai` — Direct AI Analysis

| Command | Args | Description |
|---------|------|-------------|
| `<query>` | `--prompt`, `--code`, `--repo`, `--format`, `--project-id`, `--cct-url` | Direct AI analysis via CCT Server |

---

## Response Format

All CLI commands return JSON:

```json
{
  "success": true,
  "status_code": 200,
  "message": "Operation completed",
  "data": { /* domain-specific */ },
  "meta": {
    "timestamp": "2026-05-29T...",
    "request_id": "uuid",
    "duration_ms": 123
  }
}
```

### Error response:
```json
{
  "success": false,
  "status_code": 400,
  "message": "Error description",
  "data": null,
  "error_code": "DOMAIN_ERROR_CODE"
}
```

---

## Global Flags

| Flag | Description |
|------|-------------|
| `--remote <url>` | Target remote server URL (`$CODECORTEX_REMOTE`) |
| `--cct-url <url>` | CCT server URL override (`$CCT_URL`) |
| `--pretty` | Pretty-print JSON output (default: true) |
| `--version` | Show version |
| `--help` | Show help for any command |

---

## Source of Truth

- `src/cli/__init__.py` — CLI orchestrator and domain registry
- `src/cli/common.py` — Shared helpers (`ok`, `err`, `output`, `run_async`)
- `src/modules/<domain>/api/cli.py` — Per-domain command implementations
