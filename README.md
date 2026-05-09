# CodeCortex

**The MCP-native code intelligence server for LLMs. 22 languages. 31+ tools. Zero cloud dependency.**

Every LLM can read code. CodeCortex lets them *understand* it -- tracing call chains across 50 files, detecting architecture rot before it ships, and refactoring symbols without missing a single reference. All through standard MCP tools that any AI client can call.

---

## Why CodeCortex? (VS Alternatives)

Most "code analysis" tools were built for humans reading terminals. CodeCortex was built for **LLMs calling tools** — structured JSON in, structured JSON out, with a token economy that respects context windows.

| Capability | CodeCortex | Sourcegraph/Cody | grep/ripgrep | Semgrep | CodeQL | Tree-Sitter CLI |
|---|---|---|---|---|---|---|
| **MCP-native tools** | ✅ 31+ tools | ❌ Chat-only | ❌ CLI only | ❌ CLI/IDE | ❌ CLI | ❌ CLI |
| **Structured JSON output** | ✅ Token-optimized | ❌ Markdown chat | ❌ Text lines | ❌ SARIF | ❌ SARIF | ❌ AST dump |
| **Knowledge Graph** | ✅ Dual-index O(1) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **22 languages** | ✅ Native parsing | ~30 (SaaS) | Text only | ~20 | ~15 | ~60 |
| **Framework detection** | ✅ 8 frameworks | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Route extraction** | ✅ FastAPI/Django/Flask/Express/Next.js | ❌ | ❌ | ❌ | ❌ | ❌ |
| **ORM dataflow** | ✅ SQLAlchemy/Django/Prisma | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Execution flow tracing** | ✅ BFS call chain | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Community detection** | ✅ Leiden/Louvain | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-repo (50)** | ✅ | Limited | ✅ | ✅ | ✅ | ✅ |
| **Incremental sync** | ✅ Git diff-based | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Token economy** | ✅ Auto-budget | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Offline-first** | ✅ No cloud | ❌ SaaS | ✅ | ✅ | ✅ | ✅ |
| **Disaster recovery** | ✅ Takeout/Import | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-IDE** | ✅ Any MCP client | Cody only | ✅ | IDE plugins | IDE plugins | All |
| **Windows-safe CLI** | ✅ ASCII borders | ❌ | ✅ | ✅ | ❌ | ✅ |

**The bottom line:** grep finds text. Tree-Sitter parses syntax. CodeQL runs queries. CodeCortex gives LLMs **structured, graph-based code intelligence** — the equivalent difference between handing someone a phonebook vs. a GPS map with traffic overlays.

---

## What Makes Each Feature Different

### CodeIndex — Not Just Parsing, But Understanding

**Scope:** 22 languages via Tree-Sitter 0.25.x (see full matrix below)

| Language | Parse | Symbols | Imports | Scopes | Framework Tags |
|---|---|---|---|---|---|
| Python, TypeScript, JavaScript, JSX/TSX | ✅ | ✅ | ✅ | ✅ | FastAPI/Django/Flask/Next.js/React |
| Go, Rust, Java, Kotlin | ✅ | ✅ | ✅ | ✅ | — |
| PHP, Ruby, Swift | ✅ | ✅ | ✅ | ✅ | Laravel |
| Dart/Flutter | ✅ | ✅ | ✅ | ✅ | Flutter |
| C, C++, C# | ✅ | ✅ | ✅ | ✅ | — |
| Elixir, Haskell, Perl, Lua, Zig | ✅ | ✅ | ✅ | ✅ | — |
| Bash, SQL | ✅ | ✅ | ❌ | ❌ | — |

**What sets it apart from other parsers:**

| Aspect | Tree-Sitter CLI | CodeCortex CodeIndex |
|--------|----------------|---------------------|
| Output | Raw CST dump (stdout) | Structured JSON via MCP |
| Cross-file | None | Scope resolution (6-pass) |
| Framework awareness | None | Auto-tags 8 frameworks |
| Parallelism | Single-threaded | Worker pool (CPU cores) |
| Caching | None | LRU AST cache (content hash) |
| LLM integration | Pipe to LLM manually | Native MCP tool calling |

**Flow the LLM sees:**
```
call index_repo(repo_id)
  → CodeCortex discovers files → parses (thread pool) → extracts symbols → stores
  → Returns: {repository_id, symbols_indexed: 1250, files_indexed: 47}
```

### Semantic Search — Concept Matching, Not Keyword Grep

**Unique advantage:** Uses `all-MiniLM-L6-v2` (384-dim embeddings). "User authentication" finds `login_user`, `verify_credentials`, `create_session` — none contain the exact words. Graceful fallback if model unavailable.

```
LLM → semantic_search(repo_id, "payment retry logic", top_k=5)
  → Embed query → cosine similarity → top-K ranked
  → Returns: [{score: 0.92, file: "retry.py", symbol: "retry_failed_payment", line: 15}, ...]
```

### CodeGraph — Architectural Intelligence for LLMs

**Scope:** 9 sub-features with language coverage:

| Sub-feature | Languages | What LLM Gains |
|---|---|---|
| Knowledge Graph | All 22 | O(1) symbol lookup by ID or name |
| Community Detection | All 22 | Reveals real module boundaries vs. folder structure |
| Execution Flow | All 22 (CALLS edges) | BFS call chain: "what happens when user checks out?" |
| Heritage Extraction | Python, TS, JS, Java, Go, C++, C#, PHP, Dart, Kotlin | Full class hierarchy without reading ancestor files |
| Route Extraction | FastAPI, Django, Flask, Express, Next.js | Auto-discovers API surface |
| ORM Dataflow | SQLAlchemy, Django ORM, Prisma | Extracts models, fields, relationships |
| Entry Point Scoring | All 22 | 0-100 score: identifies HTTP handlers, CLI commands |
| Architecture Audit | All 22 | God nodes, dead code, security, complexity |
| Graph Backends | Kuzu, Neo4j, FalkorDB, SQLite | Persistent graph storage |

**Flow:**
```
LLM → graph_query("callers", "process_payment")
  → KnowledgeGraph O(1): find incoming CALLS edges
  → BFS traverse up to depth
  → Returns: [{name: "checkout_cart", file: "src/api/checkout.py:42"}, {name: "retry_failed_payment", ...}]

LLM → arch_audit("repo-123", "all")
  → Graph algorithms: centrality (god nodes), degree (dead code), complexity (AST)
  → Returns: {god_nodes: [...], dead_code: [...], complexity: [...], security: [...]}
```

**Why this is different from static analysis tools:**
- Semgrep/CodeQL need you to write rules/queries. CodeCortex discovers everything automatically.
- SonarQube gives a "quality gate" pass/fail. CodeCortex gives structured JSON for LLM reasoning.

### CodeRefactor — Semantic, Graph-Aware, Safe

**Unique advantage:** Not regex search-and-replace. Knowledge Graph finds ALL references. TreeSitter identifies exact AST nodes (skips strings, comments, different namespaces). Dry-run by default. Git-commits changes. Impact analysis shows blast radius.

```
LLM → refactor_rename(path, "process_data", "calculate_metrics", dry_run=True)
  → KG finds all references → TreeSitter locates AST nodes
  → Returns: [{file: "src/order.py", line: 42, change: "old → new"}, ...]
  → LLM approves → dry_run=False → apply + git commit
```

### Token Economy — Built for LLM Context Windows

**Unique advantage:** Auto-estimates tokens, truncates to budget (2000 default), caches estimations. When response exceeds budget: optimize (remove redundant fields) → summarize (preserve key data) → truncate (last resort). LLM never sees broken JSON.

### CodeRepository — Multi-Repo, Incremental, Portable

**Unique advantages:**
- **Incremental sync**: `git diff --name-only HEAD` — 0.1s vs 60s for full re-index
- **Multi-repo**: 50 repos in one call with quota enforcement
- **Takeout/Import**: Delete-then-insert restore (disaster recovery safe)
- **Git audit**: 100+ commits scanned for secrets in seconds

---

## Who Should Use CodeCortex

| Role | What CodeCortex Does For Them |
|---|---|
| **LLM-Powered Coding Agents** | Any MCP-compatible agent (Claude Desktop, Claude Code, Cursor, Windsurf, Cline, Trae, Continue) gains deep code intelligence — call graph, heritage extraction, route discovery, architecture audit — all via structured JSON tool calls |
| **Software Architects** | Reverse-engineer the *actual* architecture vs. the *intended* one. Community detection reveals surprising cross-module coupling |
| **Senior Developers** | Navigate unfamiliar codebases at warp speed. "Trace this HTTP request to the database query" — one tool call |
| **Technical Leads** | Data-driven refactoring decisions. Impact analysis, dead code quantification, complexity hotspots |
| **Security Engineers** | Git history scan for hardcoded secrets (API keys, tokens, passwords) |
| **QA Engineers** | 23+ test runners/linters via unified MCP tools. Async execution with webhook notifications |

## Where CodeCortex Runs

| Layer | Supported |
|---|---|
| **LLM Clients** | Claude Desktop, Claude Code, Cursor, Windsurf, Cline, Trae, Continue — any MCP client |
| **Operating Systems** | Windows, macOS, Linux |
| **MCP Transports** | STDIO (default), SSE, HTTP/JSON-RPC |
| **Graph Backends** | Kuzu (embedded), Neo4j, FalkorDB, SQLite (fallback) |
| **CI/CD** | GitHub Actions (lint, test, coverage, production readiness) |

## How It Works

### Architecture: 6 Domains, One Pipeline

Built on **Domain-Driven Design** + **Hexagonal Architecture** — six autonomous bounded contexts wired via constructor injection. No global state. No magic.

```
┌──────────────────────────────────────────────────────────────┐
│                   CortexOrchestrator                        │
│                (Composition Root / DI)                       │
├──────┬───────┬───────┬───────┬───────┬───────────────────────┤
│      │       │       │       │       │                       │
│  ┌───▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌───────────────────┐
│  │Repo  │ │Index│ │Graph│ │File │ │Refac│ │     Tester       │
│  │Service│ │Service│ │Service│ │Service│ │Service│ │    Service        │
│  └──────┘ └─────┘ └─────┘ └─────┘ └─────┘ └───────────────────┘
│         └────────────┬────────────┘
│                      ▼
│             ┌────────────────┐
│             │    SQLite      │
│             │  + Graph DB    │
│             └────────────────┘
└──────────────────────────────────────────────────────────────┘
```

### The LLM Interaction Model

CodeCortex is NOT a CLI tool or a web dashboard. It is an **MCP server** — LLMs call tools, receive structured JSON, and use that data to reason about code.

```
┌──────────┐   MCP Tool Call    ┌──────────────┐   SQL/Graph    ┌──────────┐
│  LLM     │ ──────────────────>│  CodeCortex  │ ─────────────>│  SQLite  │
│  Client  │                    │  Server      │               │  + Kuzu  │
│          │ <──────────────────│              │ <─────────────│  /Neo4j  │
└──────────┘   Structured JSON   └──────────────┘   Query Result └──────────┘
     │
     │ Reads structured data, answers user
     ▼
┌──────────┐
│  User    │  "What calls process_payment?"
└──────────┘
```

### Safety First

All destructive operations default to `dry_run=True`. Path traversal prevention, SSRF guards, label sanitization, UUID validation, depth limits, quota enforcement. No auto-edit or commit without explicit approval.

---

## 31+ MCP Tools (All Work with Any MCP Client)

| Tool | Input | Output | Purpose |
|---|---|---|---|
| `repo_init` | `path, max_depth?` | `{repository_id}` | Initialize repo |
| `index_repo` | `repo_id, codemap?` | `{symbol_count, file_count}` | Full index |
| `index_file` | `repo_id, file_id` | `{symbol_count}` | Single file |
| `semantic_search` | `repo_id, query, top_k` | `[{score, file, symbol, snippet}]` | Concept search |
| `graph_find_symbols` | `search_term, type, fuzzy?` | `{functions, classes, variables}` | Find by name |
| `graph_query` | `query_type, target` | `{results, total}` | Relationships |
| `graph_trace_flow` | `symbol_id, max_depth` | Hierarchical call tree | Execution flow |
| `graph_build` | `repo_id, path` | `{build, stats}` | Build graph |
| `arch_analyze` | `repo_id?, path?` | `{communities, god_nodes, ...}` | Full architecture |
| `arch_audit` | `repo_id, audit_type` | Findings by type | Audit smells |
| `refactor_rename` | `path, old, new, dry_run` | Changes preview | Multi-file rename |
| `refactor_impact` | `path, symbol` | Blast radius | Impact analysis |
| `git_audit` | `path, limit` | Secrets findings | Security scan |
| `qa_run` | `repo_id, tool, target?` | Task ID | Run tests |
| `db_compact` | — | Space reclaimed | Database maintenance |
| `repo_cleanup` | `repo_id` | Deleted count | Remove project |
| `fs_batch` | `operations[], dry_run` | Results[] | Batch file ops |

Full list: 31+ tools across 6 domains + Core. Every tool has typed parameters and structured JSON responses.

---

## Quick Start

### Prerequisites
- Python 3.10+
- `uv` (recommended) or pip
- MCP client (Claude Desktop, Cursor, etc.)

### Install

```bash
git clone https://github.com/steevenz/mcp-codecortex.git
cd mcp-codecortex
uv sync
```

### Configure

Add to your MCP client config:

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "uv",
      "args": ["--directory", "/path/to/codecortex", "run", "python", "-m", "src.main"]
    }
  }
}
```

### Use

Tell your AI agent:

> *"Initialize this repo, index all code, and analyze the architecture."*

The agent calls `repo_init` → `index_repo` → `graph_build` → `arch_analyze` — and returns a full architectural report with communities, god nodes, entry points, and security findings.

### Docker (Graph Backends)

```bash
docker-compose up -d    # Neo4j + FalkorDB for advanced graph queries
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.10+ |
| Parsing | Tree-Sitter 0.25.x (native bindings, 22 languages) |
| Primary Store | SQLite (WAL mode, thread-safe) |
| Graph Backend | Kuzu / Neo4j / FalkorDB (optional) |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 |
| Protocol | MCP via FastMCP (STDIO / SSE / HTTP) |
| Architecture | DDD + Hexagonal + Constructor DI |

---

## Documentation

- `docs/index.md` — Executive summary
- `docs/features/support-matrix.md` — Full language, framework, backend coverage
- `docs/features/` — Per-domain docs: concept, flow, tools, output, LLM impact
- `docs/architecture/` — System design and security model

---

## License

MIT — see [LICENSE](LICENSE).

---

**Developed by [Steeven Andrian](https://github.com/steevenz) -- Senior Principal Architect, Creator of A.E.G.I.S Codework**  
**Support the project: [PayPal](https://paypal.me/steevenz)**

*CodeCortex v0.1.0 -- Scale code intelligence without friction.*
