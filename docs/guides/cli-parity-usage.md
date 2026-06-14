# CodeCortex CLI — Universal Code Intelligence Interface

CodeCortex provides a unified CLI that maps directly to its MCP tools. This allows deterministic script execution, cross-agent tool calls, and high-performance structural code reasoning without establishing an MCP connection.

## Architecture

The CLI acts as a thin transport adapter over the internal CodeCortex domain services. It supports two primary modes:
1. **Classic Mode**: Conventional positional arguments (e.g., `codecortex repo list`).
2. **Unified MCP Mode**: Direct action-based dispatch mirroring the MCP protocol.

### Entry Points
- `scripts/cli.py`: Main orchestrator for classic commands.
- `scripts/cli/codecortex_cli.py`: Unified adapter for structural tool calls.

---

## 1. Unified MCP Tool Interface

This interface is designed for programmatic consumption (JSON mode) and allows agents to call CodeCortex tools as subprocesses.

### Usage
```bash
python scripts/cli/codecortex_cli.py <tool> --action <action> --args '<json>' --json
```

### Supported Tools
| Tool | Purpose |
|------|---------|
| `repository` | Repo lifecycle (init, inspect, analyze, sync, audit, list) |
| `filesystem` | High-level file operations with auditing |
| `codebase` | Code intelligence (AST search, analysis, graph, refactor) |
| `scaffolder` | Project templates and class generation |
| `knowledge` | Knowledge graph extraction and querying |
| `idegraph` | IDE memory harvesting and context retrieval |

### Examples

**Search Code (AST + Semantic):**
```bash
python scripts/cli/codecortex_cli.py codebase --action search --args '{"query":"auth logic", "semantic":true}' --json
```

**Read File with Auditing:**
```bash
python scripts/cli/codecortex_cli.py filesystem --action read --args '{"path":"src/main.py"}' --json
```

---

## 2. Classic Positional Interface

Optimized for human operators and quick developer checks.

### Repository Management (`repo`)
- `codecortex repo init <path>`: Initialize a new project.
- `codecortex repo analyze <path>`: Run deep AST/Graph analysis.
- `codecortex repo list`: Show all indexed repositories.

### Filesystem Operations (`fs`)
- `codecortex fs tree <path>`: Display visual directory structure.
- `codecortex fs search <path> --pattern "*.py"`: Search files by pattern.

### Codebase Intelligence (`cb`)
- `codecortex cb search "<query>"`: Search code logic.
- `codecortex cb status`: Show project metrics and health.

---

## 3. JSON Contract

When using the `--json` flag, CodeCortex guarantees exactly one JSON object on `stdout`.

### Success Response
```json
{
  "success": true,
  "status_code": 200,
  "tool": "codebase",
  "action": "status",
  "data": { ... },
  "meta": {
    "adapter": "cli",
    "schema_version": 1
  }
}
```

### Error Response
```json
{
  "success": false,
  "status_code": 400,
  "error_code": "CLI_ERROR",
  "message": "Detailed error message",
  "data": {},
  "meta": { ... }
}
```

---

## 4. Environment Variables

| Variable | Description |
|----------|-------------|
| `CODECORTEX_DISABLE_AI` | Bypass CCT/AI enrichment during CLI runs |
| `CODECORTEX_LOG_LEVEL` | Set CLI verbosity (DEBUG, INFO, WARN, ERROR) |
| `CODECORTEX_PATH` | Path to CodeCortex installation (for remote bridges) |
