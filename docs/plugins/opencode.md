# CodeCortex for OpenCode CLI

OpenCode CLI supports plugins via the `.opencode/` directory + JavaScript plugin loader.

## Installation

### Option 1: Plugin auto-load (plugin.json)
Plugin is registered in `.opencode/plugin.json`. OpenCode auto-detects.

### Option 2: Via JS Plugin Loader
OpenCode also supports a JavaScript plugin loader at `.opencode/plugins/codecortex.js`.
This file reads the `.skills/` directory and registers skills.

### MCP Server
Add to OpenCode MCP config (`opencode.json`):

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

### Install via Plugin Manager
```json
{
  "plugin": ["codecortex@git+https://github.com/steevenz/mcp-codecortex.git"]
}
```

## Files

```
.opencode/
├── plugin.json               # Plugin manifest
├── INSTALL.md                # OpenCode-specific install guide
└── plugins/
    └── codecortex.js          # JS plugin loader (reads .skills/)

.skills/                       # Shared skills directory
```
