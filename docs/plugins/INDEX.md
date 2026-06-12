# Plugin Index — Supported Agents

CodeCortex provides plugin/config for **20+ AI coding agents**:

| # | Agent | Dir | Type | Since |
|---|-------|-----|------|:---:|
| 1 | [Claude Code](claude-code.md) | `.claude-plugin/` | Plugin + Hooks | v1.0 |
| 2 | [Codex CLI](codex-cli.md) | `.codex-plugin/` | Plugin | v1.0 |
| 3 | [Cursor](cursor.md) | `.cursor-plugin/` | Plugin + Hooks | v1.0 |
| 4 | [OpenCode](opencode.md) | `.opencode/` | Plugin + JS | v1.0 |
| 5 | [Trae / SOLO Trae](trae.md) | `.trae/` | MCP + Rules | v1.0 |
| 6 | [Gemini CLI](gemini-cli.md) | `.gemini-cli/` | Extension | v1.2 |
| 7 | [Antigravity CLI / IDE / Agent](antigravity-cli.md) | `.antigravity/` | MCP + Config | v1.2 |
| 8 | [Cline](cline.md) | `.cline/` | MCP + Rules | v1.2 |
| 9 | [Windsurf](windsurf.md) | `.windsurf/` | MCP + Rules | v1.2 |
| 10 | [Goose CLI](goose-cli.md) | `.goose/` | MCP + Config | v1.2 |
| 11 | [GitHub Copilot](github-copilot-cli.md) | `.github/` | Instructions | v1.2 |
| 12 | [KILO](kilo.md) | `.kilo/` | Plugin | v1.2 |
| 13 | [Continue.dev](continue.md) | `.continue/` | Agents + MCP | v1.2 |
| 14 | [Qoder / Qwen CLI](qoder.md) | `.qoder/` | MCP + Config | v1.2 |
| 15 | [Kiro IDE](kiro.md) | `.kiro/` | Agent + Skills | v1.2 |
| 16 | [Codebuddy](codebuddy.md) | (MCP config) | MCP | v1.2 |
| 17 | [Zed Editor](zed.md) | `.zed/` | MCP + Instructions | v1.2 |
| 18 | [OpenClaude](openclaude.md) | `.claude-plugin/` | Plugin (compat) | v1.2 |
| 19 | [Verdent AI](verdent.md) | `.verdent/` | Agent + MCP | v1.2 |

> **Note**: Antigravity IDE and Antigravity Agent share the same `.antigravity/` config format as Antigravity CLI.
> SOLO Trae uses the same `.trae/` config as standard Trae.
> OpenClaude uses Claude Code's `.claude-plugin/plugin.json` format (native compatibility).

## Quick Install

All plugins point to the same MCP server. Install once:

```bash
git clone https://github.com/steevenz/mcp-codecortex.git
cd mcp-codecortex
uv sync
```

Then follow each agent's install guide above.
