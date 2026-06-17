# UnifiedIndexing — Panduan Penggunaan

## Overview

UnifiedIndexing adalah orchestrator yang menggabungkan **7 index provider** dalam satu pipeline berurutan (sequential). Mendukung 3 antarmuka: **MCP Tool**, **CLI**, dan **HTTP/JSON-RPC**, plus **Background Scheduler** untuk eksekusi periodik.

## 7 Index Provider

| ID | Provider | Fungsi | Mode |
|----|----------|--------|------|
| `codecortex-full` | All providers | Index semua provider berurutan (default) | full / incremental |
| `codecortex-codeindex` | Code Index | AST indexing via tree-sitter (symbols, files, edges) | full / incremental / files |
| `codecortex-graph` | Graph | Graph database build (dependency + modular) | full |
| `codecortex-embeddings` | Embeddings | Vector embeddings via sentence-transformers | full |
| `codecortex-knowledge` | Knowledge | Knowledge graph extraction (document chunks) | full |
| `codecortex-idegraph` | IDE Memory | Cross-IDE conversation/memory harvest | full |
| `codecortex-codelogs` | Logs | Log file discovery & indexing | full |
| `codecortex-security` | Security | Security scan (secrets, vulns, PII, misconfig) | full |

Mode: `full` (re-index lengkap), `incremental` (hanya file berubah via git diff).

---

## 1. MCP Tool

**Tool name:** `codecortex:indexing`

### Run full indexing pipeline

```json
{
  "action": "run",
  "repo_path": "/home/user/project",
  "provider": "codecortex-full",
  "mode": "full"
}
```

### Run specific provider only

```json
{
  "action": "run",
  "repo_path": "/home/user/project",
  "provider": "codecortex-codeindex",
  "mode": "full"
}
```

### Incremental indexing (git diff)

```json
{
  "action": "run",
  "repo_path": "/home/user/project",
  "provider": "codecortex-full",
  "mode": "incremental"
}
```

### Start periodic scheduler

```json
{
  "action": "schedule",
  "repo_path": "/home/user/project",
  "interval": 3600
}
```

### Stop scheduler

```json
{
  "action": "stop"
}
```

### Check scheduler status + last run

```json
{
  "action": "status"
}
```

### List available providers

```json
{
  "action": "providers"
}
```

### Parameter lengkap

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | string | `"run"` | `run` / `schedule` / `stop` / `status` / `providers` |
| `repo_path` | string | — | Repository path (wajib untuk run/schedule) |
| `repo_id` | string | — | Repository UUID (alternatif untuk run) |
| `provider` | string | `"codecortex-full"` | Provider ID |
| `mode` | string | `"full"` | `full` / `incremental` |
| `interval` | int | `3600` | Interval scheduler dalam detik (min: 60) |
| `args` | dict | — | Params tambahan (detect_modular, embedding_model, severity, dll) |

### Response

```json
{
  "success": true,
  "status_code": 200,
  "message": "Indexing completed — 7/7 steps successful",
  "data": {
    "provider": "codecortex-full",
    "repo_path": "/home/user/project",
    "success": true,
    "total_elapsed_seconds": 145.3,
    "steps": [
      {
        "provider": "codecortex-codeindex",
        "status": "completed",
        "elapsed_seconds": 30.5,
        "details": {
          "symbol_count": 1500,
          "file_count": 250
        }
      },
      {
        "provider": "codecortex-security",
        "status": "completed",
        "elapsed_seconds": 5.2,
        "details": {
          "findings_count": 3
        }
      }
    ]
  },
  "meta": { "duration_ms": 145300 }
}
```

---

## 2. CLI

```bash
# Run full indexing pipeline (semua 7 provider)
codecortex indexing run /home/user/project
codecortex idx run /home/user/project
codecortex index run /home/user/project

# Provider spesifik
codecortex indexing run /home/user/project --provider codecortex-codeindex
codecortex indexing run /home/user/project --provider codecortex-graph
codecortex indexing run /home/user/project --provider codecortex-embeddings
codecortex indexing run /home/user/project --provider codecortex-knowledge

# Incremental mode
codecortex indexing run /home/user/project --mode incremental

# Periodic scheduler
codecortex indexing schedule /home/user/project --interval 3600
codecortex indexing schedule /home/user/project --interval 1800  # setiap 30 menit

# Stop scheduler
codecortex indexing stop

# Cek status scheduler + last run
codecortex indexing status

# List semua provider
codecortex indexing providers

# JSON output
codecortex indexing run /home/user/project --json
```

### CLI Aliases

| Perintah | Alias | Fungsi |
|----------|-------|--------|
| `codecortex indexing run` | `idx run` / `index run` | Run indexing |
| `codecortex indexing schedule` | `idx schedule` | Start scheduler |
| `codecortex indexing stop` | `idx stop` | Stop scheduler |
| `codecortex indexing status` | `idx status` | Check status |
| `codecortex indexing providers` | `idx providers` | List providers |

### CLI Parameters

| Argumen | Short | Default | Description |
|---------|-------|---------|-------------|
| `repo_path` | (posisi) | — | Repository path |
| `--provider` | `-p` | `codecortex-full` | Provider ID |
| `--mode` | `-m` | `full` | `full` / `incremental` |
| `--repo-id` | `-r` | — | Repository UUID |
| `--interval` | `-i` | `3600` | Scheduler interval (detik) |
| `--json` | — | `false` | Raw JSON output |
| `--no-modular` | — | `true` | Nonaktifkan modular detection |
| `--no-dependency-graph` | — | `true` | Nonaktifkan dependency graph |

---

## 3. HTTP API

### POST `/v1/index` — Run indexing

```bash
curl -X POST http://127.0.0.1:8001/v1/index \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/home/user/project",
    "provider": "codecortex-full",
    "mode": "full"
  }'
```

### POST `/v1/index/schedule` — Start scheduler

```bash
curl -X POST http://127.0.0.1:8001/v1/index/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/home/user/project",
    "interval": 3600
  }'
```

### POST `/v1/index/stop` — Stop scheduler

```bash
curl -X POST http://127.0.0.1:8001/v1/index/stop
```

### GET `/v1/index/status` — Check status

```bash
curl http://127.0.0.1:8001/v1/index/status
```

### GET `/v1/index/providers` — List providers

```bash
curl http://127.0.0.1:8001/v1/index/providers
```

---

## 4. Python API (direct)

```python
import asyncio
from src.services.unified_indexing import IndexingRequest, get_indexing_engine

engine = get_indexing_engine()

# Run full pipeline
req = IndexingRequest(
    provider="codecortex-full",
    repo_path="/home/user/project",
    mode="full",
    sequential=True,
)
result = asyncio.run(engine.index(req))
print(f"Success: {result.success}")
for step in result.steps:
    print(f"  [{step.status.value}] {step.provider} — {step.elapsed_seconds:.1f}s")
    if step.error:
        print(f"    Error: {step.error}")

# Start scheduler
engine.start_scheduler("/home/user/project", interval_seconds=3600)

# Check status
status = engine.scheduler_status()
print(f"Scheduler running: {status['running']}")

# Stop scheduler
engine.stop_scheduler()
```

---

## 5. Verifikasi Integrasi dengan UnifiedSearch

Setelah UnifiedIndexing selesai, data langsung tersedia untuk UnifiedSearch:

```bash
# 1. Index semua data
codecortex indexing run /home/user/project

# 2. Verifikasi dengan search
codecortex search "class UserService" --model codecortex-codebase --repo-path /home/user/project
codecortex search "my_function" --model codecortex-graph --repo-path /home/user/project
codecortex search "architecture" --model codecortex-knowledge --repo-path /home/user/project

# 3. Incremental update
codecortex indexing run /home/user/project --mode incremental

# 4. Search tetap berfungsi setelah incremental
codecortex search "new_feature" --model codecortex-combo --repo-path /home/user/project
```

Pipeline verifikasi lengkap:

| Langkah | Perintah | Expected |
|---------|----------|----------|
| Full index | `codecortex indexing run /repo` | 7/7 steps successful |
| Search symbols | `codecortex s "class" --model codecortex-codebase` | Results ditemukan |
| Search graph | `codecortex s "MyClass" --model codecortex-graph` | Relationships ditemukan |
| Search knowledge | `codecortex s "docstring" --model codecortex-knowledge` | Document chunks ditemukan |
| Incremental | `codecortex indexing run /repo --mode incremental` | 7/7 steps, lebih cepat |
| Search after | `codecortex s "symbol" --model codecortex-combo` | Data masih fresh |

---

## 6. Provider Reference

| Provider | Required | Optional | Error jika tanpa required |
|----------|----------|----------|--------------------------|
| `codecortex-codeindex` | repo_path atau repo_id | mode, files | `failed` — "Could not resolve repo_id" |
| `codecortex-graph` | repo_id | detect_modular, build_dependency_graph | `skipped` — "repo_id required" |
| `codecortex-embeddings` | repo_id | model | `skipped` — "repo_id required" |
| `codecortex-knowledge` | repo_path | knowledge_types | `failed` — "Not a directory" |
| `codecortex-idegraph` | repo_path | project_name | `failed` — "Not a directory" |
| `codecortex-codelogs` | repo_path | search_paths | `failed` — "Not a directory" |
| `codecortex-security` | repo_path | file_pattern, severity | `failed` — "Not a directory" |

Resource usage:
- **codeindex**: CPU-intensive (tree-sitter parsing). Gunakan `mode=incremental` untuk update cepat.
- **embeddings**: GPU-optional (sentence-transformers). Fallback ke CPU jika GPU tidak tersedia.
- **graph**: Memory-intensive untuk repository besar. Gunakan `detect_modular=false` untuk mempercepat.
- **security**: I/O-bound. Cepat selesai karena hanya scan pattern matching.

---

## 7. Troubleshooting

| Masalah | Penyebab | Solusi |
|---------|----------|--------|
| Scheduler tidak berjalan | Path tidak valid | Gunakan absolute path, pastikan direktori ada |
| Indexing lambat | Mode `full` di repo besar | Gunakan `mode=incremental` |
| Graph build skipped | Tidak ada `repo_id` | Jalankan `codecortex repo inspect /path` dulu |
| Embeddings skipped | Tidak ada `repo_id` | Sama seperti graph — pastikan repo terdaftar |
| Security scan cepat | Pattern matching sederhana | Normal — security scan seharusnya cepat |

---

## 8. Referensi Dokumentasi

| Dokumen | Link |
|---------|------|
| **UnifiedIndexing konsep** | `docs/features/unified-indexing/concept.md` |
| **UnifiedSearch konsep** | `docs/features/unified-search/concept.md` |
| **UnifiedSearch usage** | `docs/features/unified-search/usage.md` |
| **Source code** | `src/services/unified_indexing.py` |
| **MCP tool registration** | `src/api/tools.py` (TOOL 7: codecortex:indexing) |
| **CLI** | `src/cli/indexing.py` |
| **HTTP server** | `scripts/server/http.py` |
| **Tests** | `tests/unit/test_unified_indexing.py` |
