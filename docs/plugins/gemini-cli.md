# CodeCortex for Gemini CLI

## Prerequisites
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed
- CodeCortex MCP server running

## Installation

### 1. MCP Server
Add to Gemini CLI config:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "gemini-cli"]
    }
  }
}
```

### 2. Copy extension directory
```bash
cp -r .gemini-cli/extensions/codecortex ~/.gemini-cli/extensions/
```

Or to project root:
```bash
cp -r .gemini-cli /path/to/your/project/
```

### 3. Verify
```bash
gemini-cli --extension .gemini-cli/extensions/codecortex
```

## Usage

Gemini CLI loads the CodeCortex extension automatically. Use MCP tools directly:
- `codecortex:codebase(action=search, args={query:"..."})`
- `codecortex:codebase(action=analyze, args={target:"..."})`
- etc.

## Files

```
.gemini-cli/
├── mcp.json                              # MCP server config
└── extensions/codecortex/
    ├── extension.json                    # Extension manifest
    ├── system_prompt.md                  # CodeCortex policy
    └── rules.md                          # CodeCortex rules
```
