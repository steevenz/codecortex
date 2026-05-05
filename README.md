# CodeCortex

**Scale code intelligence without friction.** CodeCortex is a multi-domain intelligence engine that transforms raw codebases into semantic knowledge graphs through Domain-Driven Design and MCP integration.

---

## 🎯 The Problem

Modern codebases are complex beasts—thousands of files, tangled dependencies, and hidden architectural debt. Traditional tools either:
- **Overwhelm** developers with raw syntax trees
- **Miss** semantic relationships between components
- **Fail** to provide actionable architectural insights
- **Cost** a fortune in API credits for large repositories

CodeCortex bridges this gap by providing **deep semantic understanding** through AST parsing, relationship mapping, and architectural analysis—all exposed through Model Context Protocol (MCP).

---

## ✨ Key Features

### 🧠 Semantic Code Indexing
- **20+ Languages**: Native Tree-Sitter parsing for Python, TypeScript, JavaScript, Go, Rust, Java, C#, and more
- **Symbol Extraction**: Automatic detection of classes, functions, variables, imports, and their nested scopes
- **Incremental Updates**: Hash-based manifest tracking for efficient re-indexing
- **Zero Dependencies**: Pure AST analysis without external compiler requirements

### 🏗️ Architectural Intelligence
- **Call Graph Construction**: Maps function calls, inheritance hierarchies, and module dependencies
- **God Node Detection**: Identifies high-coupling components that threaten system stability
- **Temporal Hotspots**: Pinpoints frequently changed files that indicate technical debt
- **Community Detection**: Leiden/Louvain algorithms reveal surprising cross-domain connections
- **Security Auditing**: Automatic scanning for hardcoded secrets (API keys, tokens, passwords)

### 🔍 Intelligent Search
- **Symbol-Based Search**: Find classes, functions, and variables across the entire codebase
- **Regex Support**: Pattern matching for complex symbol queries
- **Execution Flow Tracing**: Recursively trace call graphs from entry points to dependencies
- **Fuzzy Search**: Portable backend abstraction for similarity-based symbol discovery

### 🛠️ Safe Code Transformation
- **Dependency-Aware Refactoring**: Understand impact before changing code
- **Git Integration**: Preserve history and enable rollback
- **Impact Analysis**: Identify all affected components before transformation
- **Safe Operations**: Guarded file operations with path validation

### ✅ Quality Assurance
- **Test Discovery**: Automated detection of test files and test suites
- **Coverage Analysis**: Measure test coverage across modules
- **Quality Metrics**: Comprehensive reporting on code health
- **Regression Detection**: Identify potential breaks before deployment

### 🔒 Security-First Design
- **SSRF Prevention**: Guards against Server-Side Request Forgery attacks
- **Path Traversal Protection**: Prevents directory escape vulnerabilities
- **Label Sanitization**: Safe handling of graph labels in HTML outputs
- **Input Validation**: Comprehensive validation for all user inputs

---

## 🧪 The Tech Review

### Why Domain-Driven Design (DDD)?

**Bounded Contexts** enforce single responsibility, preventing god classes and enabling independent evolution. CodeCortex decomposes into six autonomous domains:

1. **CodeRepository**: Physical discovery, Git sync, manifest tracking
2. **CodeIndex**: AST parsing, symbol extraction, SQLite persistence
3. **CodeGraph**: Call graph construction, relationship mapping, graph backend writes
4. **Filesystem**: File operations abstraction, path validation, I/O safety
5. **CodeRefactor**: Safe code transformation, dependency-aware refactoring
6. **CodeTester**: Quality assurance, test discovery, coverage analysis

Each domain owns its data, logic, and boundaries—wired together via **Constructor Injection (DI)** for testability and loose coupling.

### Why Hexagonal Architecture?

External dependencies (Git, Tree-Sitter, Graph DBs) are wrapped in **adapters**, not leaked into domain logic. This means:
- **Pure Domain Logic**: Business rules remain untainted by infrastructure concerns
- **Easy Testing**: Mock adapters for unit tests without touching real systems
- **Swappable Backends**: Switch between Neo4j, Kùzu, or FalkorDB without changing domain code

### Why SQLite + Graph Backend Hybrid?

**SQLite** provides structured metadata with fast queries and ACID guarantees for symbol tables. **Graph Databases** (Neo4j/Kùzu/FalkorDB) excel at complex relationship queries like "find all functions that call this class." The hybrid approach gives you the best of both worlds:
- **Fast Metadata**: Symbol lookups in milliseconds via SQLite
- **Deep Relationships**: Traversal queries in graph databases
- **Atomic Coordination**: `DatabaseManager` ensures consistent writes across both backends

### Why MCP (Model Context Protocol)?

**MCP** provides a standardized interface for AI agents to interact with tools. CodeCortex exposes its intelligence as MCP tools, enabling:
- **Seamless Integration**: Works with Claude Desktop, Cursor, and other MCP-compatible clients
- **Type-Safe Tooling**: Structured input/output schemas prevent hallucinations
- **Transport Flexibility**: stdio, SSE, or HTTP/JSON-RPC depending on deployment needs

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- uv (recommended) or pip
- Claude Desktop or MCP-compatible client

### Installation

```bash
# Clone the repository
git clone https://github.com/steevenz/.aicoders.git
cd scripts/pythons/codecortex

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### MCP Configuration

Add to your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "codecortex": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/codecortex",
        "run",
        "python",
        "-m",
        "src.main"
      ]
    }
  }
}
```

### HTTP Server Mode (Optional)

For web deployments or custom integrations:

```bash
# Set environment variables
export CODECORTEX_DASHBOARD_API_KEY="your-secret-key"
export CODECORTEX_HOST="127.0.0.1"
export CODECORTEX_PORT="8001"

# Run HTTP server
python -m src.main
```

The server exposes MCP tools via HTTP/JSON-RPC at `http://127.0.0.1:8001/codecortex-api/v1/sync`.

---

## 🔧 Available MCP Tools

### Core Analysis
- **`analyze_codebase(path)`**: Full pipeline—index, graph build, and architectural analysis
- **`index_codebase(path)`**: Index repository for semantic search
- **`get_architecture_summary(path)`**: High-level architectural metrics and insights
- **`get_structured_codemap(path)`**: Hierarchical tree of directories, files, and symbols

### Search & Traversal
- **`search_symbols(path, query, is_regex, limit)`**: Symbol search with regex support
- **`trace_execution_flow(symbol_id, max_depth)`**: Recursive call graph tracing
- **`suggest_questions(path, top_n)`**: AI-driven exploration questions from graph heuristics

### Graph Analysis
- **`graph_diff(path)`**: Compare graph snapshots for node/edge deltas
- **`find_community_surprises(path, top_n)`**: Detect surprising cross-community connections

### Security
- **`validate_url_safe(url)`**: SSRF-safe URL validation
- **`validate_graph_path_safe(path, base_path)`**: Path traversal prevention
- **`sanitize_graph_label(text)`**: Label sanitization for graph outputs

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CortexOrchestrator                       │
│                  (Composition Root / DI)                      │
├──────┬───────┬───────┬───────┬───────┬──────────────────────┤
│      │       │       │       │       │                      │
│  ┌───▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──────────────────────┐
│  │Repo │ │Index│ │Graph│ │File │ │Refac│ │      Tester       │
│  │Service│ │Service│ │Service│ │Service│ │Service│ │   Service         │
│  └───┬──┘ └───┬──┘ └───┬──┘ └───┬──┘ └───┬──┘ └──────────────────────┘
│      │        │        │        │        │        │
│      └────────┴────────┴────────┴────────┴────────┘
│                           │
│                           ▼
│              ┌────────────────────┐
│              │    SQLite DB      │
│              │  (Metadata +       │
│              │   Manifest)        │
│              └────────┬───────────┘
│                       │
│                       ▼
│              ┌────────────────────┐
│              │  Graph Backend     │
│              │ (Neo4j/Kùzu/        │
│              │  FalkorDB)          │
│              └────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Technology Stack

- **Language**: Python 3.10+
- **Architecture**: Domain-Driven Design (DDD), Hexagonal Architecture
- **Database**: SQLite + Neo4j/Kùzu/FalkorDB (optional)
- **Parsing**: Tree-Sitter (native bindings, 20+ languages)
- **Protocol**: MCP (Model Context Protocol) via FastMCP
- **Transport**: stdio, SSE, HTTP/JSON-RPC
- **Standards**: Aegis Codeworks v1.0

---

## 📝 License

This project is licensed under the MIT License.

---

**Developed with ❤️ by [Steeven Andrian](https://github.com/steevenz) | [Support via PayPal](https://paypal.me/steevenz)**
*Senior Principal Architect | Founder/Creator A.E.G.I.S Codework*
