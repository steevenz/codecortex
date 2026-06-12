# CodeCortex for KILO

KILO is an open source AI coding agent for VS Code, JetBrains, CLI, and Cloud. It supports plugins via `.kilo/` directory.

## Installation

Add to your `.kilo/config.json`:

```json
{
  "plugins": [
    {
      "name": "codecortex",
      "source": "./.kilo/codecortex"
    }
  ],
  "mcpServers": {
    "codecortex": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-codecortex", "run", "python", "-m", "src.main"]
    }
  }
}
```

## Files

```
.kilo/
├── config.json          # KILO plugin config
└── codecortex/
    ├── plugin.json      # Plugin manifest
    └── rules.md         # CodeCortex rules for KILO
```
