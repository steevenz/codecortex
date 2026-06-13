# CodeCortex for Qoder CLI / Qwen CLI

Qoder (by Alibaba) is an agentic coding platform with desktop, IDE plugin, and CLI support.

## Installation

### CLI
Configure MCP in `~/.qoder/config.yaml` or project-level `.qoder/config.yaml`:

```yaml
mcp_servers:
  codecortex:
    command: node
    args:
      - /path/to/mcp-codecortex/scripts/server/js/index.cjs
      - --ide
      - qoder
```

### VS Code / JetBrains Plugin
Add CodeCortex MCP server in Qoder settings → MCP Servers.

## Files

```
.qoder/
├── config.yaml         # Qoder CLI config (MCP server)
└── rules.md            # CodeCortex rules for Qoder
```
