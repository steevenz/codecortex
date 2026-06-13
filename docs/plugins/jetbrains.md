# CodeCortex for JetBrains (IntelliJ, PyCharm, WebStorm, etc.)

JetBrains IDE has **built-in MCP support** since version 2025.2. Two JetBrains products relate to AI:

1. **JetBrains AI Assistant** — Built-in AI assistant (MCP built-in)
2. **Junie** — Cloud-based AI coding agent

---

## Method 1: Built-in MCP (IntelliJ IDEA 2025.2+)

### Prerequisites
- IntelliJ-based IDE (IDEA, PyCharm, WebStorm, GoLand, etc.) **2025.2+**
- CodeCortex MCP server running

### Setup

#### Step 1: Install CodeCortex MCP Server
```bash
git clone https://github.com/steevenz/mcp-codecortex.git
cd mcp-codecortex
uv sync
```

#### Step 2: Configure MCP in JetBrains IDE

**Via Settings UI:**
1. `File → Settings → Tools → MCP Server`
2. Click `+` to add new server
3. Fill:
   - **Name**: `codecortex`
   - **Command**: `node`
   - **Arguments**: `/path/to/mcp-codecortex/scripts/server/js/index.cjs --ide jetbrains`
4. Click OK

**Via file config (`.idea/mcp.json`):**
```json
{
  "servers": {
    "codecortex": {
      "command": "node",
      "args": ["/path/to/mcp-codecortex/scripts/server/js/index.cjs", "--ide", "jetbrains"]
    }
  }
}
```

> On Windows, use the path to `node.exe` if `node` is not globally available:
> ```json
> {
>   "servers": {
>     "codecortex": {
>       "command": "C:\\Program Files\\nodejs\\node.exe",
>       "args": ["C:\\path\\to\\mcp-codecortex\\scripts\\server\\js\\index.cjs", "--ide", "jetbrains"]
>     }
>   }
> }
> ```

#### Step 3: Verify
- MCP server connects automatically
- CodeCortex tools available in AI Assistant and Junie
- Try: "Analyze this codebase using codecortex"

---

## Method 2: Via JetBrains MCP Proxy (Legacy)

For IDE versions < 2025.2, use MCP Proxy:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "npx",
      "args": ["-y", "@jetbrains/mcp-proxy"],
      "env": {
        "IDE_PORT": "YOUR_IDE_PORT"
      }
    }
  }
}
```

Then register CodeCortex as a custom tool in the MCP Server Plugin.

---

## Method 3: Custom MCP Tool Extension (Plugin Devs)

For developers wanting a custom MCP plugin, the JetBrains MCP Server Plugin previously provided extension points. **Now built-in.**

References:
- [JetBrains MCP Server Plugin (deprecated)](https://github.com/JetBrains/mcp-server-plugin)
- [JetBrains MCP Proxy](https://github.com/JetBrains/mcp-jetbrains)
- [Official MCP Docs](https://www.jetbrains.com/help/idea/mcp-server.html)

---

## About Junie

**Junie** is JetBrains' cloud-based AI coding agent. Junie can access projects in JetBrains IDE via MCP. By configuring CodeCortex as an MCP server in the IDE, Junie can use all CodeCortex tools for codebase analysis.

---

## Files

```
.idea/
└── mcp.json              # Project-level MCP config (JetBrains)
.idea/
└── codecortex-rules.md   # CodeCortex usage rules
```
