# Installing CodeCortex for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation via Plugin Manager

Add CodeCortex to the `plugin` array in your `opencode.json` (global or project-level):

```json
{
  "plugin": ["codecortex@git+https://github.com/steevenz/mcp-codecortex.git"]
}
```

Restart OpenCode. The plugin installs through OpenCode's plugin manager and registers all CodeCortex skills.

## Manual Installation

```bash
git clone https://github.com/steevenz/mcp-codecortex.git
```

Then in `opencode.json`:

```json
{
  "plugin": ["/path/to/mcp-codecortex"]
}
```

## Usage

After installation, use OpenCode's native `skill` tool:

```
use skill tool to list skills
use skill tool to load codecortex-codebase
use skill tool to load codecortex-knowledge
```

## MCP Server Configuration

CodeCortex also requires its MCP server to function. Configure in your OpenCode MCP settings:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-codecortex", "run", "python", "-m", "src.main"]
    }
  }
}
```

## Troubleshooting

1. Check logs: `opencode run --print-logs "hello" 2>&1 | grep -i codecortex`
2. Verify the plugin line in your `opencode.json`
3. Make sure the MCP server is configured (CodeCortex tools require it)

## Tool Mapping for Skills

When skills reference Claude Code tools:
- `codecortex:codebase` etc. → OpenCode MCP tool calls
- `Skill` tool → OpenCode's native `skill` tool
- File operations → OpenCode native tools
