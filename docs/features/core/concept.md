# Core: Shared Infrastructure

> **Package:** `src/core/`

## Concept

Core provides shared infrastructure used by all domains: database management, token economy, CLI interface, and utilities.

## Components

| Component | File | Purpose |
|-----------|------|---------|
| **Database** | `database.py` | SQLite with 10 tables, WAL mode, thread-safe connections |
| **Graph Manager** | `graph_manager.py` | Kuzu/Neo4j/FalkorDB backend abstraction |
| **Token Economy** | `token_economy.py` | Token estimation, smart summarize, budget enforcement |
| **Database Cleanup** | `database_cleanup.py` | VACUUM, REINDEX, project data removal |
| **Takeout/Import** | `takeout.py` | Portable project export/import |
| **API Response** | `errors.py` | Standardized `{success, data, meta}` envelope |
| **MCP Compliance** | `mcp-compliance.md` | Annotations, progress, resources, logging, duration |
| **Logging** | `logging_config.py` | Structured JSON logging + MCP logging notifications |
| **Telemetry** | `telemetry.py` | OpenTelemetry tracing |

## Sub-Features

- [Token Economy](sub-features/token-economy/concept.md)
- [Database Maintenance](sub-features/database-maintenance/operations.md)
- [CLI](sub-features/cli/commands.md)
