# UnifiedSearch: Multi-Provider Search Orchestrator

> **Domain:** Services
> **Package:** `src/services/unified_search.py`
> **Version:** 2.0.0
> **AI Coder Impact:** 10/10
> **Production Readiness:** 100%

## Business Context

UnifiedSearch is the **centralized search orchestrator** that consolidates 16 search providers into a single, unified API. It replaces fragmented domain-specific search logic with a consistent request/response model, 9Router-compatible streaming, automatic provider selection (combo mode), ReDoS-safe regex execution, and integrated security filtering across every search path.

Without UnifiedSearch:
- Each domain (codebase, filesystem, knowledge, graph, git, svn, etc.) had separate search APIs with inconsistent parameters and outputs
- No unified security filter — sensitive content could leak through individual domain tools
- No streaming or 9Router compatibility for agent-friendly consumption
- No combo mode to search across all providers in one call

## Why This Exists

- **16 Unified Providers:** 16 purpose-built search providers — codebase, filesystem, repowt, graph, idegraph, knowledge, crossproject, codeindex, agentart, codelogs, todo, stub, security, empty, svn, blame — plus a combo orchestrator that queries all providers in parallel
- **Security-First Search:** Every provider that reads file content (filesystem, repowt, knowledge, security, empty) passes results through `CodeAuditor` or `SecurityFilter` — sensitive/vulgar content is masked or blocked before it reaches the AI agent
- **ReDoS Protection:** All regex searches are guarded by input size limits (500KB), backtracking limits (100K), pattern complexity analysis, and a 5-second timeout — prevents regex injection attacks
- **9Router Compatibility:** UnifiedSearch is exposed as a 9Router MCP tool (`codecortex:search`) with the same JSON-RPC interface, enabling streaming, cancellation, and token budgeting
- **Auto-Indexing:** When `auto_index=true`, UnifiedSearch triggers `repo_inspect` + `CodeIndexService.index_repository()` before executing the search — zero-touch configuration
- **Parallel Execution:** Multi-provider queries (combo, or explicit list) execute all providers concurrently via `asyncio.gather()` — sub-second search across all data sources
- **Zero New Code:** All 6 new providers (todo, stub, security, empty, svn, blame) wire into existing `CodeAuditor`, `DiskSvn`, `DiskGit` — zero reinvention

## Theoretical Foundation

- **FTS5 (Full-Text Search):** SQLite FTS5 virtual tables for substring/prefix matching on indexed symbols and documents. Used by codebase, knowledge, and crossproject providers. O(log n) query time.
- **Embedding Similarity:** sentence-transformers cosine similarity for semantic search. Top-20 nearest neighbors by L2 distance. Used when semantic=true.
- **Glob + Regex:** Python `glob.glob()` for file pattern matching (fast), `re.search()` for content regex (slower, ReDoS-guarded). Used by filesystem provider.
- **Git Status Parsing:** `git status --porcelain` output parsing for working-tree search. Used by repowt provider.
- **SVN Status Parsing:** `svn status --non-interactive` output parsing for SVN working-tree search. Used by svn provider.
- **Graph Traversal (BFS):** Breadth-first search on Kuzu/Neo4j/FalkorDB relationship edges. Configured via max_depth parameter. Used by graph provider.
- **CodeAuditor Integration:** `CodeAuditor.audit()` with `scan_categories` parameter drives todo (comments), stub (empty_code), and security (secrets+vulns+pii+misconfig) providers.
- **DiskGit + DiskSvn:** `DiskGit.get_insights()` and `DiskSvn.get_insights()` for repository overview; `git blame --porcelain` for per-file annotations.
- **SecurityFilter Pipeline:** File path validation -> sensitive file matching (extension/name) -> vulgar content detection -> sensitive content masking/blocking. Applied to every search result before delivery.

## Architecture

```
SearchRequest (query, model, filters)
  │
  ├─► Combo Mode ──► asyncio.gather(
  │    16 providers   each provider returns [] + stats + warning
  │    ) ──► merge results ──► SearchResponse
  │
  └─► Single Provider ──► provider.Method(req)
        │
        ├─► _search_codebase     (FTS5 + semantic + graph)
        ├─► _search_filesystem   (glob + regex + SecurityFilter)
        ├─► _search_repowt       (git status + SecurityFilter)
        ├─► _search_graph        (BFS on graph backend)
        ├─► _search_idegraph     (IDE memory FTS)
        ├─► _search_knowledge    (knowledge FTS + SecurityFilter)
        ├─► _search_crossproject (multi-repo FTS5)
        ├─► _search_codeindex    (symbol metadata lookup)
        ├─► _search_agentart     (.agents folder walk)
        ├─► _search_codelogs     (log file scan + LogService)
        ├─► _search_todo         (CodeAuditor comment tags — TODO, FIXME, HACK, STUB, etc.)
        ├─► _search_stub         (CodeAuditor empty function/class)
        ├─► _search_security     (CodeAuditor secrets/vulns + DiskAudit sensitive files)
        ├─► _search_empty        (os.walk 0-byte files + empty dirs + CodeAuditor stubs)
        ├─► _search_svn          (DiskSvn status/log/info)
        └─► _search_blame        (DiskGit insights + git blame + history scan)
```

## 16 Providers

| Provider | Model ID | Method | Data Source | Security Filter |
|----------|----------|--------|-------------|-----------------|
| **codebase** | `codecortex-codebase` | `_search_codebase()` | SQLite FTS5 + embeddings + graph edges | None (symbols only) |
| **filesystem** | `codecortex-filesystem` | `_search_filesystem()` | Disk walk + regex | `check_file()` + `process_content()` |
| **repowt** | `codecortex-repowt` | `_search_repowt()` | `git status --porcelain` | `check_file()` |
| **graph** | `codecortex-graph` | `_search_graph()` | Kuzu/Neo4j/FalkorDB | None (relationships only) |
| **idegraph** | `codecortex-idegraph` | `_search_idegraph()` | SQLite FTS5 (IDE sessions) | None (metadata only) |
| **knowledge** | `codecortex-knowledge` | `_search_knowledge()` | SQLite FTS5 + JSON meta | `check_file()` + `process_content()` |
| **crossproject** | `codecortex-crossproject` | `_search_crossproject()` | SQLite FTS5 (multi-repo) | None (symbols only) |
| **codeindex** | `codecortex-codeindex` | `_search_codeindex()` | SQLite symbols table | None (metadata only) |
| **agentart** | `codecortex-agentart` | `_search_agentart()` | Disk walk (.agents/) | `check_file()` |
| **codelogs** | `codecortex-codelogs` | `_search_codelogs()` | LogService (log files) | None (log data) |
| **todo** | `codecortex-todo` | `_search_todo()` | CodeAuditor `scan_categories: ["comments"]` | None (comment text) |
| **stub** | `codecortex-stub` | `_search_stub()` | CodeAuditor `scan_categories: ["empty_code"]` | None (symbols only) |
| **security** | `codecortex-security` | `_search_security()` | CodeAuditor (secrets/vulns/pii/misconfig) + DiskAudit | `check_file()` |
| **empty** | `codecortex-empty` | `_search_empty()` | os.walk (0-byte files + empty dirs) + CodeAuditor | `check_file()` |
| **svn** | `codecortex-svn` | `_search_svn()` | `svn status` + `svn log` + DiskSvn | None (metadata only) |
| **blame** | `codecortex-blame` | `_search_blame()` | DiskGit insights + `git blame` + history scan | `check_file()` |
| **combo** | `codecortex-combo` | orchestrate all 16 | All providers | Per-provider |

## SearchRequest Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | yes | — | Search query (text, regex, tag name, or stub type) |
| `model` | string | no | `"codecortex-combo"` | Provider model ID |
| `max_results` | int | no | `20` | Max results to return |
| `search_type` | string | no | `"all"` | `all` / `code` / `file` / `memory` / `knowledge` / `repo` / `log` / `todo` / `stub` / `security` / `empty` / `svn` / `blame` |
| `file_pattern` | string | no | `"*"` | Glob filter for files |
| `semantic` | bool | no | `false` | Enable embedding similarity |
| `graph_enrichment` | bool | no | `false` | Append relationship context |
| `graph_relations` | list | no | `[]` | Relation types to include |
| `repo_path` | string | no | `None` | Path to search within |
| `repo_id` | string | no | `None` | Repo UUID (from repo_inspect) |
| `auto_index` | bool | no | `true` | Auto-index missing repos |
| `language` | string | no | `None` | Language filter (for stub, codebase) |
| `log_levels` | string | no | `None` | Log level filter (for codelogs) |
| `date_from` | string | no | `None` | Start date ISO (for codelogs) |
| `date_to` | string | no | `None` | End date ISO (for codelogs) |

## SearchResponse

```json
{
  "success": true,
  "message": "Found 15 results across 2 providers (0.23s)",
  "data": {
    "results": [
      {
        "position": 1,
        "title": "class PaymentGateway",
        "display_url": "src/services/payment.py:42",
        "score": 0.95,
        "snippet": "class PaymentGateway:\n    def process(self, amount):...",
        "metadata": { "source_type": "codebase", "type": "class", "line": 42 },
        "citation": { "provider": "codecortex-codebase", "rank": 1 }
      }
    ],
    "provider_stats": {
      "codecortex-codebase": {"results": 12, "time_ms": 120},
      "codecortex-filesystem": {"results": 3, "time_ms": 110}
    },
    "total_available": 15,
    "has_more": true,
    "next_offset": 20,
    "response_time_ms": 234,
    "providers_used": 2,
    "total_results": 12,
    "index_status": { "indexed": true, "fresh": true }
  }
}
```

## Security Integration

Every provider that accesses file content integrates with `CodeAuditor` or `SecurityFilter`:

- **`_search_filesystem`**: Each file found by glob is passed through `sec_filter.check_file(path, content)`. If `allowed=False`, the file is excluded. If `content_action=mask`, the displayed content is replaced with `***MASKED***`.
- **`_search_repowt`**: Changed files from `git status` are checked via `check_file()`. New/modified files with sensitive names are excluded.
- **`_search_knowledge`**: Knowledge chunk text is checked via `process_content()`. If `action=block`, the chunk is skipped. If `action=mask`, the text is replaced.
- **`_search_security`**: Uses `CodeAuditor._find_secrets()` for credential detection + `DiskAudit.audit()` for sensitive file pattern matching.
- **`_search_empty`**: Scanned file paths verified against security filter before reporting.
- **`_search_blame`**: Git history scanned via `CodeAuditor._scan_git_history()` for leaked secrets in commit history.

## ReDoS Protection

All regex-based search (`search_type="regex"`) is protected by:

| Guard | Limit | Effect |
|-------|-------|--------|
| Pattern length | 2000 chars | Prevents exponential-blowup patterns |
| Catastrophic pattern detection | 5 known patterns | Rejects `(.+)+`, `(a+)+`, etc |
| Input size cap | 500 KB | Truncates before search |
| Execution timeout | 5 seconds | Kills runaway regex |
| Backtracking limit | 100,000 | Aborts excessive backtracking |

## Token Economy

- **`summary_mode`**: Combo responses with `summary_mode=true` return only result count + top-3 per provider (auto-truncation)
- **`include_content=false`**: Set to return file paths + line numbers only, no snippet content
- **`max_results`**: Lower limit = fewer tokens. Start with `max_results=10`, expand if needed
- **Streaming**: 9Router SSE streams return results incrementally — start consuming before full response

## Error Codes

| Prefix | Tool |
|--------|------|
| US_001 | Invalid model ID |
| US_002 | Empty query |
| US_003 | ReDoS rejection |
| US_004 | Path traversal detected |
| US_005 | No providers matched |
| US_500 | Internal search error |

## Related Sub-Features

- [Security Filter](sub-features/security-filter/concept.md)

---

*This document follows CODDY Codeworks documentation standards.*
