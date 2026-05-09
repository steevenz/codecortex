# CLI: Command Line Interface

> **Source:** `scripts/cli.py`, `scripts/formatter.py`

## Concept

The CLI provides terminal access to CodeCortex operations without an MCP client. Output is formatted in Laravel Artisan style with ASCII-safe borders and ANSI colors.

## Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `--repositories` | `--projects` | List all registered repositories |
| `--workspaces` | — | (Coming soon) List workspaces |
| `--compact <repo_id>` | — | VACUUM + REINDEX database |
| `--cleanup <repo_id>` | — | Delete all data for a project (IRREVERSIBLE) |
| `--takeout <repo_id>` | — | Export project to portable JSON |
| `--import-dump <path>` | — | Import project from JSON dump |
| `--output-dir <dir>` | — | Custom output directory for exports |
| `--init <path>` | — | Initialize a repository |
| `--status` | — | Show server status (online/offline) |
| `--git-audit <path>` | — | Scan git history for secrets |
| `--list-repos` | — | List all indexed repositories |
| `--version` | — | Show version |
| `--help` | — | Show help |

## Output Format

The formatter produces ASCII tables with:

```
##########################################################
  REGISTERED REPOSITORIES
##########################################################
  # ID            | NAME    | PATH                  | STATUS
  +--------------+---------+-----------------------+--------
  # abc-123      | my-app  | C:/Projects/my-app    | active
  # def-456      | my-lib  | C:/Projects/my-lib    | stale
  ##########################################################
  Total repositories: 2
```

- **Colors:** Green (headers), Yellow (data), Cyan (IDs), Red (errors)
- **ASCII-safe:** Uses `#`, `+`, `-`, `|` — no Unicode box-drawing characters
- **Compatible:** Works in Windows cmd, PowerShell, and all terminals
