# UnifiedSearch — Panduan Penggunaan

## Overview

UnifiedSearch adalah orchestrator yang menggabungkan **16 search provider** dalam satu API. Mendukung 3 antarmuka: **MCP Tool**, **CLI**, dan **HTTP/JSON-RPC (9Router)**.

## 16 Search Provider

| ID | Provider | Fungsi |
|----|----------|--------|
| `codecortex-combo` | All providers | Search semua provider paralel (default) |
| `codecortex-codebase` | Codebase | FTS5 + semantic + graph symbol search |
| `codecortex-filesystem` | Filesystem | Glob filename + content regex |
| `codecortex-repowt` | Repo WT | Git working-tree: status, diff, commits |
| `codecortex-graph` | Graph | BFS call chain, relationships |
| `codecortex-idegraph` | IDE Memory | Cross-IDE session search |
| `codecortex-knowledge` | Knowledge | Knowledge graph FTS |
| `codecortex-crossproject` | Cross-project | Multi-repo symbol lookup |
| `codecortex-codeindex` | Code Index | Symbol metadata lookup |
| `codecortex-agentart` | Agent Artifacts | `.agents/` folder search |
| `codecortex-codelogs` | Logs | Log file search with level/time filters |
| `codecortex-todo` | Comment Tags | TODO, FIXME, HACK, XXX, STUB, BUG, OPTIMIZE, REVIEW, DEPRECATED, dan 7 tag lainnya |
| `codecortex-stub` | Stubs | Fungsi kosong, class kosong, placeholder (pass, NotImplementedError) |
| `codecortex-security` | Security | Secrets (AWS keys, tokens), vulnerabilities, PII, misconfig, file audit |
| `codecortex-empty` | Empty | File 0 byte, folder kosong, empty function/class |
| `codecortex-svn` | SVN | SVN working-tree: status, log, info |
| `codecortex-blame` | Git Blame | `git blame` per-file, commit hotspots, repo insights |

Search type shortcut: `all` (default), `code`, `file`, `memory`, `knowledge`, `repo`, `log`, `todo`, `stub`, `security`, `empty`, `svn`, `blame`.

---

## 1. MCP Tool

**Tool name:** `codecortex:search`

### Cari semua provider (combo)

```json
{
  "action": "search",
  "query": "payment gateway",
  "model": "codecortex-combo",
  "max_results": 20
}
```

### Cari spesifik provider

```json
{
  "action": "search",
  "query": "class UserService",
  "model": "codecortex-codebase",
  "repo_path": "/home/user/project"
}
```

### Cari TODO/FIXME/HACK tags

```json
{
  "action": "search",
  "query": "FIXME",
  "model": "codecortex-todo",
  "repo_path": "/home/user/project"
}
```

> Query opsional — kosongkan untuk semua tag, isi "FIXME" untuk filter spesifik.

### Cari fungsi kosong / stub

```json
{
  "action": "search",
  "query": "",
  "model": "codecortex-stub",
  "repo_path": "/home/user/project",
  "language": "python"
}
```

### Cari security issues

```json
{
  "action": "search",
  "query": "",
  "model": "codecortex-security",
  "repo_path": "/home/user/project"
}
```

### Cari file/folder kosong

```json
{
  "action": "search",
  "query": "",
  "model": "codecortex-empty",
  "repo_path": "/home/user/project"
}
```

### Cari SVN working-tree

```json
{
  "action": "search",
  "query": "",
  "model": "codecortex-svn",
  "repo_path": "/home/user/project"
}
```

### Cari git blame + hotspots

```json
{
  "action": "search",
  "query": "auth",
  "model": "codecortex-blame",
  "repo_path": "/home/user/project"
}
```

### Cari file + content regex

```json
{
  "action": "search",
  "query": "api key",
  "model": "codecortex-filesystem",
  "repo_path": "/home/user/project",
  "file_pattern": "*.py",
  "content_regex": "secret|password"
}
```

### Cari git working-tree

```json
{
  "action": "search",
  "query": "fix",
  "model": "codecortex-repowt",
  "repo_path": "/home/user/project",
  "status_filter": "modified"
}
```

### Cari log files

```json
{
  "action": "search",
  "query": "RuntimeError",
  "model": "codecortex-codelogs",
  "repo_path": "/home/user/project",
  "log_levels": "ERROR,CRITICAL",
  "date_from": "2026-06-01"
}
```

### List provider available

```json
{
  "action": "models"
}
```

### Info detail provider

```json
{
  "action": "info",
  "model": "codecortex-filesystem"
}
```

### Parameter lengkap

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | string | `"search"` | `search` / `models` / `info` |
| `query` | string | — | Search query (optional untuk todo/stub/security/empty/svn) |
| `model` | string | `"codecortex-combo"` | Provider ID |
| `provider` | string | — | Alias untuk model |
| `max_results` | int | `20` | Max 200 |
| `search_type` | string | `"all"` | `all` / `code` / `file` / `memory` / `knowledge` / `repo` / `log` / `todo` / `stub` / `security` / `empty` / `svn` / `blame` |
| `repo_path` | string | — | Path repo |
| `repo_id` | string | — | UUID repo |
| `file_pattern` | string | `"*"` | Glob pattern |
| `content_regex` | string | — | Regex konten |
| `auto_index` | bool | `true` | Auto-index jika kosong |
| `force_update` | bool | `false` | Paksa update index |
| `regraph` | bool | `false` | Rebuild graph |
| `reindex` | bool | `false` | Rebuild code index |
| `log_levels` | string | — | Filter level log (codelogs) |
| `date_from` | string | — | Filter tanggal mulai (codelogs) |
| `date_to` | string | — | Filter tanggal akhir (codelogs) |
| `language` | string | — | Filter bahasa (stub, codebase) |
| `args` | dict | — | Params tambahan (symbol_type, language, direction, dll) |

### Response (9Router-compatible)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Found 12 results across 2 providers (0.23s)",
  "data": {
    "results": [
      {
        "position": 1,
        "title": "src/services/payment.py - class PaymentGateway",
        "display_url": "src/services/payment.py:42",
        "score": 0.95,
        "snippet": "class PaymentGateway:\n    def process(self, amount):...",
        "metadata": { "source_type": "codebase", "type": "class", "line": 42 },
        "citation": { "provider": "codecortex-codebase", "rank": 1 }
      }
    ],
    "provider_stats": {
      "codecortex-codebase": { "results_found": 8, "latency_ms": 120 },
      "codecortex-filesystem": { "results_found": 4, "latency_ms": 110 }
    },
    "total_available": 15,
    "has_more": true,
    "next_offset": 20,
    "response_time_ms": 234,
    "providers_used": 2,
    "total_results": 12,
    "index_status": { "indexed": true, "fresh": true }
  },
  "meta": { "duration_ms": 250 }
}
```

---

## 2. CLI

```bash
# Cari semua provider
codecortex search "payment gateway"
codecortex s "payment gateway"
codecortex find "payment gateway"

# Provider spesifik
codecortex search "UserService" --model codecortex-codebase
codecortex search "api key" --model codecortex-filesystem --file-pattern "*.py"
codecortex search "bug fix" --model codecortex-repowt --status-filter modified

# New providers
codecortex search "FIXME" --model codecortex-todo
codecortex search "" --model codecortex-stub --language python
codecortex search "" --model codecortex-security
codecortex search "" --model codecortex-empty
codecortex search "" --model codecortex-svn
codecortex search "auth" --model codecortex-blame

# Search type shortcut
codecortex search "class User" --type code
codecortex search "README" --type file
codecortex search "meeting notes" --type memory
codecortex search "architecture decision" --type knowledge
codecortex search "WIP" --type repo
codecortex search "RuntimeError" --type log
codecortex search "FIXME" --type todo
codecortex search "" --type stub
codecortex search "" --type security
codecortex search "" --type empty
codecortex search "" --type svn
codecortex search "auth" --type blame

# Filter
codecortex search "payment" --repo-path /home/user/project
codecortex search "auth" --language python --max-results 50
codecortex search "token" --content-regex "ghp_|sk-" --model codecortex-filesystem

# Pagination
codecortex search "api" --max-results 10 --offset 10

# Action
codecortex search models
codecortex search "query" --json

# Nonaktifkan auto-index
codecortex search "query" --no-auto-index

# Paksa rebuild index
codecortex search "query" --repo-path /home/user/project --force-update
```

### CLI Aliases

| Perintah | Alias | Fungsi |
|----------|-------|--------|
| `codecortex search` | `s` / `find` / `unified-search` | Search query |
| `codecortex search models` | — | List providers |

### CLI Parameters

| Argumen | Short | Default | Description |
|---------|-------|---------|-------------|
| `query` | (posisi) | — | Search query (optional untuk beberapa provider) |
| `--model` | `-m` | `codecortex-combo` | Provider ID |
| `--type` | `-t` | `all` | Search type |
| `--max-results` | `-n` | `20` | Max results |
| `--offset` | — | `0` | Pagination offset |
| `--repo-path` | `-p` | — | Repository path |
| `--repo-id` | `-r` | — | Repository UUID |
| `--file-pattern` | — | `*` | File glob |
| `--content-regex` | — | — | Content regex |
| `--max-depth` | — | `20` | Directory depth |
| `--symbol-type` | — | `any` | `any` / `function` / `class` / `variable` |
| `--language` | `-l` | — | Language filter |
| `--status-filter` | — | — | Git status filter |
| `--since` | — | — | Git since date |
| `--artifact-type` | — | — | `.agents` type filter |
| `--json` | — | `false` | Raw JSON output |
| `--force-update` | — | `false` | Force index update |
| `--no-auto-index` | — | `false` | Disable auto-index |

---

## 3. HTTP API (9Router / internal)

Endpoint: `POST /codecortex-api/v1/sync`

```bash
curl -X POST http://127.0.0.1:8001/codecortex-api/v1/sync \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "codecortex:search",
    "args": {
      "action": "search",
      "query": "payment gateway",
      "model": "codecortex-combo",
      "max_results": 10,
      "repo_path": "/home/user/project"
    }
  }'
```

```bash
# List providers
curl -X POST http://127.0.0.1:8001/codecortex-api/v1/sync \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "codecortex:search",
    "args": { "action": "models" }
  }'
```

---

## 4. Python API (direct)

```python
import asyncio
from src.services.unified_search import SearchRequest, get_search_engine

engine = get_search_engine()

# Combo search
req = SearchRequest(
    query="class PaymentGateway",
    model="codecortex-combo",
    max_results=20,
    repo_path="/home/user/project",
    auto_index=True,
)
response = asyncio.run(engine.search(req))
for r in response.results:
    print(f"[{r.score:.2f}] {r.title} — {r.display_url}")

# Todo search
req2 = SearchRequest(
    query="FIXME",
    search_type="todo",
    repo_path="/home/user/project",
)
response = asyncio.run(engine.search(req2))

# Security search
req3 = SearchRequest(
    model="codecortex-security",
    repo_path="/home/user/project",
)
response = asyncio.run(engine.search(req3))
```

---

## 5. Security Filter (built-in)

Semua provider yang mengakses konten file otomatis melewati **SecurityFilter** atau **CodeAuditor**:

- **Default mode** (`CODECORTEX_SECURITY_STRICT=false`): konten sensitif (password, token, API key) di-*masking* jadi `***MASKED***`, file tetap muncul
- **Strict mode** (`CODECORTEX_SECURITY_STRICT=true`): konten sensitif di-*block*, file tidak muncul
- **Vulgar/NSFW**: selalu di-block, tidak pernah sampai ke hasil pencarian
- **File sensitif** (`.env`, `.key`, `id_rsa`, dll): selalu di-block
- **CodeAuditor**: deteksi 15 jenis comment tags, 4 kategori security (secrets, vulns, pii, misconfig), Shannon entropy scoring

Tidak perlu konfigurasi tambahan — otomatis aktif.

---

## 6. ReDoS Protection (built-in)

| Guard | Limit |
|-------|-------|
| Pattern length | Max 2000 chars |
| Input size | Max 500 KB (truncated) |
| Execution timeout | 5 detik |
| Backtrack limit | 100.000 |

---

## 7. Referensi Dokumentasi

| Dokumen | Link |
|---------|------|
| **UnifiedSearch konsep** | `docs/features/unified-search/concept.md` |
| **SecurityFilter referensi** | `docs/features/unified-search/sub-features/security-filter/concept.md` |
| **Security architecture** | `docs/architecture/security.md` (section Service Security) |
| **Search workflow** | `docs/workflows/search-discovery-workflow.md` |
| **Changelog** | `docs/versions/changelog.md` (entry 2026-06-17) |
| **Source code** | `src/services/unified_search.py` |
| **MCP tool registration** | `src/api/tools.py` (TOOL 6: codecortex:search) |
| **CLI** | `src/cli/search.py` |
