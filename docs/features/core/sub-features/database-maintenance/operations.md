# Database Maintenance

> **Source:** `src/core/database_cleanup.py`, `src/core/takeout.py`

## Operations

### Compact (VACUUM)

Reclaims disk space and optimizes database performance.

```
Usage: python scripts/cli.py --compact <repo_id>
  or:  db_compact() MCP tool

What it does:
  1. ROLLBACK (end any active transaction)
  2. VACUUM (rebuild database file, reclaim space)
  3. REINDEX (rebuild all indexes)
  4. ANALYZE (update query planner statistics)

Safe: No data loss, can run anytime.
```

### Cleanup (Project Deletion)

Permanently removes ALL data for a project from the database.

```
Usage: python scripts/cli.py --cleanup <repo_id>
  or:  repo_cleanup() MCP tool

What it deletes:
  - files, directories, symbols, edges, insights
  - commits, file_commits, manifest_entries
  - repository record
  - global registry entry (~/.codecortex/registry.json)

IRREVERSIBLE: Use with caution. Re-run repo_init to re-index.
```

### Takeout (Export)

Exports all project data to a portable JSON file.

```
Usage: python scripts/cli.py --takeout <repo_id> --output-dir <dir>

What it exports:
  - repositories, directories, files, symbols, edges
  - insights, manifest_entries, commits, file_commits

Format: Single JSON file with all tables as arrays.
```

### Import (Restore)

Restores a project from a takeout dump file.

```
Usage: python scripts/cli.py --import-dump <path>

Import strategy:
  1. Upsert repository record
  2. DELETE + INSERT for all child tables (clean restore)
  3. Preserves existing data from other projects

Disaster recovery: Wipes stale data before importing fresh data.
```
