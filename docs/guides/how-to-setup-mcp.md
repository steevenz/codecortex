# How to Set Up CodeCortex MCP Server

Complete guide to installing, configuring, and connecting CodeCortex as an MCP server to your AI coding assistant.

---

## Overview

CodeCortex uses a **Node.js + Python** architecture:

```
IDE ──stdio──► Node (index.cjs) ──HTTP/SSE──► Python (src/main.py)
```

| Layer | Role | Required |
|-------|------|----------|
| **Node.js** (`index.cjs`) | MCP stdio proxy, multi-IDE lifecycle, file-lock concurrency, JSON-RPC forwarding | **✅ Required** |
| **Python** (`src/main.py`) | MCP server core: code intelligence, graph, filesystem, refactoring | Auto-managed by Node |

> **IMPORTANT**: All IDE MCP configs must point to **Node.js** (`index.cjs`), NOT directly to Python. Direct Python mode is deprecated and will cause PID conflicts in multi-IDE setups.

---

## Prerequisites

| Dependency | Version | Purpose |
|------------|---------|---------|
| **Node.js** | >= 18.0.0 | **Required** — MCP proxy server + lifecycle manager |
| **Python** | >= 3.10 | MCP server backend (auto-discovered by Node) |
| **Git** | any | Repository sync operations |

---

## Step 1: Clone & Install

```bash
git clone https://github.com/steevenz/codecortex.git
cd mcp-codecortex

# Install Python dependencies
uv sync
# or: pip install -e .
```

---

## Step 2: Configure Environment

```bash
# Copy template
cp .env.example .env

# Generate API key
python scripts/server/keygen.py --install
```

Your `.env` must contain:

```env
CODECORTEX_CLIENT_API_KEY=codecortex_client_xxxx...
```

---

## Step 3: Add to Your IDE MCP Config

### 🔴 CRITICAL: All IDE configs MUST define `--ide` flag

CodeCortex uses the `--ide` flag to identify which IDE is connecting. This enables:
- Instance identity in lockfile handshake
- Multi-IDE conflict prevention
- Proper lifecycle reference counting

### Generic JSON Config

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": [
        "C:/Users/steevenz/MCP/mcp-codecortex/scripts/server/js/index.cjs",
        "--ide",
        "<YOUR_IDE_NAME>"
      ]
    }
  }
}
```

Replace `<YOUR_IDE_NAME>` with:
| IDE | `--ide` value |
|-----|---------------|
| Trae | `trae` |
| Cursor | `cursor` |
| VS Code | `vscode` |
| Windsurf | `windsurf` |
| Claude Desktop | `claude` |
| Claude Code CLI | `claude-code` |
| Cline | `cline` |
| Continue | `continue` |
| OpenCode | `opencode` |
| Other | `<your-ide-name>` |

---

## Client-Specific Configurations

### Trae

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": [
        "C:/Users/steevenz/MCP/mcp-codecortex/scripts/server/js/index.cjs",
        "--ide",
        "trae"
      ]
    }
  }
}
```

### Cursor

Settings → Cursor Settings → MCP → Add New MCP Server:

| Field | Value |
|-------|-------|
| Name | `codecortex` |
| Type | `command` |
| Command | `node C:/Users/steevenz/MCP/mcp-codecortex/scripts/server/js/index.cjs --ide cursor` |

### VS Code (MCP Extension)

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "codecortex": {
      "command": "node",
      "args": [
        "C:/Users/steevenz/MCP/mcp-codecortex/scripts/server/js/index.cjs",
        "--ide",
        "vscode"
      ]
    }
  }
}
```

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": [
        "C:/Users/steevenz/MCP/mcp-codecortex/scripts/server/js/index.cjs",
        "--ide",
        "claude"
      ]
    }
  }
}
```

### Windsurf

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "node",
      "args": [
        "C:/Users/steevenz/MCP/mcp-codecortex/scripts/server/js/index.cjs",
        "--ide",
        "windsurf"
      ]
    }
  }
}
```

### Claude Code CLI

```bash
claude mcp add codecortex -- node C:/path/to/scripts/server/js/index.cjs --ide claude-code
```

---

## How It Works: Multi-IDE Handshake

When multiple IDEs connect to CodeCortex simultaneously:

```
IDE-A (Trae)     IDE-B (Cursor)    Python (Shared)
    │                 │                 │
    │── index.cjs ────┤                 │
    │── file lock ────┤                 │
    │── spawn ────────┼──── SSR ───────►│
    │                 │                 │
    │                 │── index.cjs ────┤
    │                 │── file lock ────┤
    │                 │── connect ──────┤
    │                 │   HTTP/SSE      │
    │                 │                 │
    │ [close]         │                 │
    │── refCount-- ───┤                 │
    │                 │ [close]         │
    │                 │── refCount=0 ───┤
    │                 │── kill ────────►│
```

- **First IDE** spawns Python backend via HTTP/SSE
- **Subsequent IDEs** detect existing server → reuse via reference counting
- **Last disconnect** shuts down Python backend automatically

---

## IDE Identity Detection

CodeCortex detects which IDE is connecting through a two-layer system:

### Layer 1: Explicit `--ide` flag (Recommended)

Always pass `--ide <name>` in your MCP config args. This is the most reliable method.

### Layer 2: Environment variable auto-detection

If `--ide` is not provided, Node auto-detects from environment:

| Variable | Detected IDE |
|----------|--------------|
| `TRAE_ID` | `trae` |
| `VSCODE_NLS_CONFIG` | `vscode` |
| `TERM_PROGRAM=cursor` | `cursor` |

Auto-detection is useful for CLI-based agents but should not be relied upon for IDE integrations.

---

## Python Mode (Deprecated)

Direct Python mode (`python src/main.py`) is **deprecated** and should only be used for testing:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "python",
      "args": ["-u", "src/main.py"],
      "cwd": "C:/Users/steevenz/MCP/mcp-codecortex",
      "env": {
        "CODECORTEX_CLIENT_API_KEY": "your-key-here",
        "PYTHONPATH": "C:/Users/steevenz/MCP/mcp-codecortex"
      }
    }
  }
}
```

**Warnings:**
- ❌ No multi-IDE lifecycle management
- ❌ No reference counting (PID conflicts with shared server)
- ❌ No auto-detection of existing instances
- ❌ No graceful shared shutdown
- ⚠️ Use only for single-IDE development or debugging

---

## Transport Modes

### STDIO (Default — IDE Integration)

Used when connecting via MCP clients. Node wraps stdio and forwards HTTP/SSE to Python backend.

### HTTP/SSE (Shared Server Mode)

Set `CODECORTEX_TRANSPORT=sse` in `.env` to force HTTP/SSE transport. Node spawns Python with HTTP and proxies all requests.

---

## Troubleshooting

### "Shared server failed to become ready"
- Ensure Python dependencies are installed: `uv sync`
- Check `.env` has valid `CODECORTEX_CLIENT_API_KEY`
- Verify no stale Python process on port 8001: `taskkill /F /IM python.exe /FI "WINDOWTITLE eq codecortex"`

### PID cascade kill loop
- Clear killed-PID cache: `del %USERPROFILE%\.codecortex\codecortex.killed`
- Clear lockfile: `del %USERPROFILE%\.codecortex\codecortex.pid`
- Verify all configs use `node index.cjs --ide <name>` (not direct Python)

### "ModuleNotFoundError: CODDY"
```bash
# Restore missing module
git checkout HEAD -- src/modules/codegraph/services/coddy.py
```
