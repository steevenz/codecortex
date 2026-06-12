# CodeCortex for Qoder CLI / Qwen CLI

Qoder (by Alibaba) is an agentic coding platform with desktop, IDE plugin, and CLI support.

## Installation

### CLI
Configure MCP in `~/.qoder/config.yaml` or project-level `.qoder/config.yaml`:

```yaml
mcp_servers:
  codecortex:
    command: uv
    args:
      - --directory
      - /path/to/mcp-codecortex
      - run
      - python
      - -m
      - src.main
```

### VS Code / JetBrains Plugin
Add CodeCortex MCP server in Qoder settings → MCP Servers.

## Files

```
.qoder/
├── config.yaml         # Qoder CLI config (MCP server)
└── rules.md            # CodeCortex rules for Qoder
```
