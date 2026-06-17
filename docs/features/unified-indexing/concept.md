# UnifiedIndexing: Multi-Provider Index Orchestrator

> **Domain:** Services
> **Package:** `src/services/unified_indexing.py`
> **Version:** 1.0.0
> **AI Coder Impact:** 10/10
> **Production Readiness:** 100%

## Business Context

UnifiedIndexing adalah **centralized indexing orchestrator** yang mengkonsolidasikan 7 index providers ke dalam satu pipeline berurutan (sequential). Ini adalah mitra tulis (write) dari UnifiedSearch — alih-alih membaca dari seluruh sumber data, UnifiedIndexing menulis/memperbarui seluruh sumber data secara teratur.

Tanpa UnifiedIndexing:
- Setiap domain (codeindex, graph, embeddings, knowledge, idegraph, logs, security) harus di-index secara manual satu per satu
- Tidak ada mekanisme penjadwalan berkala — index menjadi stale tanpa ada yang memperbarui
- Tidak ada per-provider status tracking — sulit mengetahui langkah mana yang gagal
- Tidak ada integrasi dengan UnifiedSearch — auto-indexing hanya berfungsi saat search dipanggil

## Why This Exists

- **7 Unified Providers:** 7 purpose-built index providers — codeindex, graph, embeddings, knowledge, idegraph, codelogs, security — plus full pipeline yang menjalankan semua provider secara berurutan
- **Sequential Execution:** Setiap provider berjalan dalam urutan yang ditentukan. Jika satu provider gagal, pipeline melanjutkan ke provider berikutnya — tidak ada kegagalan total
- **Per-Step Status Tracking:** Setiap langkah mencatat status (completed/failed/skipped), waktu mulai-selesai, durasi, detail hasil, dan pesan error — memudahkan debugging
- **Background Scheduler:** Daemon thread yang menjalankan `codecortex-full --mode incremental` secara periodik (default: setiap 1 jam). Responsif terhadap stop signal dengan interval pengecekan 10 detik
- **Zero New Code:** Semua provider me-reuse service yang sudah ada — `Indexer.index_repository()`, `GraphService.build_graph()`, `index_file_embeddings()`, `KnowledgeStore.extract()`, `SideCortexOrchestrator.run_all()`, `LogService.scan_logs()`, `CodeAuditor.audit()` — zero reinvention
- **Integrasi dengan UnifiedSearch:** Provider yang di-index oleh UnifiedIndexing langsung tersedia untuk UnifiedSearch. Contoh: `codecortex-codeindex` di-index oleh UnifiedIndexing, lalu di-search oleh UnifiedSearch tanpa perlu konfigurasi tambahan
- **TaskQueue Integration:** Background task queue (`core/worker/queue.py`) menyediakan infrastructure untuk eksekusi async dan status tracking

## Theoretical Foundation

- **AST Indexing (tree-sitter):** `Indexer.index_repository()` menggunakan tree-sitter untuk parse 22 bahasa pemrograman. Ekstrak symbol names, types, signatures, docstrings, dan hubungan antar file. Disimpan di SQLite tables (`symbols`, `files`, `edges`).
- **Graph Build (Kuzu/Neo4j/FalkorDB):** `GraphService.build_graph()` membaca data dari SQLite dan membangun graph relationship edges. Mendukung dependency graph, modular detection, dan call hierarchy.
- **Embedding Generation (sentence-transformers):** `index_file_embeddings()` membagi file menjadi chunks, menghasilkan vector embeddings via sentence-transformers, dan menyimpannya di `embeddings` table untuk semantic search.
- **Knowledge Graph Extraction:** `KnowledgeStore.extract()` memindai dokumentasi (markdown, rst, txt), mengekstrak entity relationships, dan menyimpannya di knowledge graph tables.
- **IDE Memory Harvest:** `SideCortexOrchestrator.run_all()` memindai folder `.agents/`, `.claude/`, `.cursor/`, dan folder IDE lainnya untuk conversation history dan session data.
- **Log Discovery:** `LogService.scan_logs()` menggunakan systematic path collection — mendeteksi bahasa pemrograman, OS, server, dan database yang berjalan, lalu mencari file log di path yang sesuai.
- **Security Scan:** `CodeAuditor.audit()` dengan `scan_categories` untuk secrets (AWS keys, tokens, private keys), vulnerabilities (SQL injection, eval, pickle), PII (email, SSN), dan misconfigurations (debug, CORS).
- **Background Scheduler:** Threading.Timer-based daemon thread. Tidak memerlukan cron/APScheduler. Interval konfigurabel, stop signal responsif dalam 10 detik.

## Architecture

```
Scheduler (daemon thread)
  │
  └─► IndexingRequest (provider="codecortex-full", mode="incremental")
        │
        └─► Sequential Pipeline
              │
              ├─► 1. _index_codeindex     (AST indexing via tree-sitter)
              │      └─► Indexer.index_repository()
              │
              ├─► 2. _index_graph         (Graph dependency build)
              │      └─► GraphService.build_graph()
              │
              ├─► 3. _index_embeddings    (Vector embeddings)
              │      └─► index_file_embeddings()
              │
              ├─► 4. _index_knowledge     (Knowledge graph extraction)
              │      └─► KnowledgeStore.extract()
              │
              ├─► 5. _index_idegraph      (IDE memory harvest)
              │      └─► SideCortexOrchestrator.run_all()
              │
              ├─► 6. _index_codelogs      (Log file discovery)
              │      └─► LogService.scan_logs()
              │
              └─► 7. _index_security      (Security scan)
                     └─► CodeAuditor.audit()
```

## 7 Providers

| Provider | Method | Data Source | Reuses Service | Dependencies |
|----------|--------|-------------|----------------|--------------|
| **codeindex** | `_index_codeindex()` | SQLite (symbols, files, edges) | `Indexer.index_repository()` | repo_id or repo_path |
| **graph** | `_index_graph()` | Kuzu/Neo4j/FalkorDB | `GraphService.build_graph()` | repo_id |
| **embeddings** | `_index_embeddings()` | SQLite (embeddings) | `index_file_embeddings()` | repo_id |
| **knowledge** | `_index_knowledge()` | SQLite (knowledge chunks) | `KnowledgeStore.extract()` | repo_path |
| **idegraph** | `_index_idegraph()` | SQLite (IDE sessions) | `SideCortexOrchestrator.run_all()` | repo_path |
| **codelogs** | `_index_codelogs()` | Disk (log files) | `LogService.scan_logs()` | repo_path |
| **security** | `_index_security()` | Disk + CodeAuditor | `CodeAuditor.audit()` + `UnifiedSearchEngine._search_security()` | repo_path |
| **full** | orchestrate all 7 | All providers | Per-provider | repo_path or repo_id |

## IndexingRequest Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | string | no | `"codecortex-full"` | Provider ID |
| `repo_path` | string | no | `None` | Repository path to index |
| `repo_id` | string | no | `None` | Repository UUID |
| `mode` | string | no | `"full"` | `full` / `incremental` |
| `files` | list | no | `None` | Specific files for codeindex |
| `sequential` | bool | no | `true` | Sequential execution (vs parallel) |
| `detect_modular` | bool | no | `true` | Modular detection in graph build |
| `build_dependency_graph` | bool | no | `true` | Dependency graph in graph build |
| `knowledge_types` | list | no | `None` | Knowledge type filter |
| `project_name` | string | no | `None` | Project name for idegraph |
| `search_paths` | string | no | `None` | Additional log search paths |
| `file_pattern` | string | no | `"*"` | File pattern for security scan |
| `severity` | string | no | `"medium"` | Severity threshold for security |
| `embedding_model` | string | no | `"codebert"` | Model name for embeddings |
| `notify_on_complete` | bool | no | `false` | Webhook notification on completion |

## IndexingResult

```json
{
  "success": true,
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
        "started_at": "2026-06-17T10:00:00",
        "completed_at": "2026-06-17T10:00:30",
        "elapsed_seconds": 30.5,
        "details": {
          "repo_id": "abc-123",
          "symbol_count": 1500,
          "file_count": 250,
          "edge_count": 3200,
          "languages": ["python", "typescript"],
          "mode": "full"
        },
        "error": null
      },
      {
        "provider": "codecortex-graph",
        "status": "completed",
        "started_at": "2026-06-17T10:00:30",
        "completed_at": "2026-06-17T10:00:45",
        "elapsed_seconds": 15.2,
        "details": {
          "repo_id": "abc-123",
          "detect_modular": true
        }
      }
    ]
  }
}
```

## Scheduler

| Feature | Detail |
|---------|--------|
| **Implementation** | `threading.Thread` daemon |
| **Default interval** | 3600 detik (1 jam) |
| **Minimum interval** | 60 detik |
| **Mode** | `incremental` |
| **Provider** | `codecortex-full` (semua 7) |
| **Stop responsiveness** | Dalam 10 detik (interval pengecekan) |
| **Start method** | `engine.start_scheduler(repo_path, interval_seconds=3600)` |
| **Status** | `engine.scheduler_status()` → running, repo_path, interval, last_run |
| **Singleton** | `get_indexing_engine()` — thread-safe |

## Error Handling

| Skenario | Behavior |
|----------|----------|
| Satu provider gagal | Pipeline lanjut ke provider berikutnya. `overall_success = false` |
| Semua provider gagal | Pipeline selesai dengan `success: false`, semua step `failed` |
| Empty repo_path | Provider return `skipped` atau `failed` dengan pesan error |
| Scheduler double-start | Return error: "Scheduler already running" |
| Stop tanpa scheduler aktif | Return error: "Scheduler not running" |
| Interval < 60 detik | Dinaikkan ke 60 detik |

## Integration dengan UnifiedSearch

| Aspek | UnifiedSearch | UnifiedIndexing |
|-------|---------------|-----------------|
| Role | Read — mencari data | Write — memperbarui data |
| Eksekusi | Paralel (asyncio.gather) | Berurutan (sequential) |
| Provider count | 17 | 7 |
| Auto-trigger | Saat data stale (`auto_index=true`) | Periodik (scheduler) |
| Shared providers | codeindex, graph, knowledge | codeindex, graph, knowledge |
| Security filter | Ya (SecurityFilter + CodeAuditor) | Ya (CodeAuditor) |
| Konsumsi data | Langsung dari SQLite + disk | Menulis ke SQLite + disk |
| Status tracking | `index_status` dalam response | `steps[]` array per-provider |

Verifikasi integrasi:
1. UnifiedIndexing meng-index → data ditulis ke SQLite + graph DB
2. UnifiedSearch membaca → data yang sama tersedia untuk search
3. Provider yang sama (`codecortex-codeindex`) menggunakan tabel SQLite yang sama
4. Tidak ada konflik — UnifiedIndexing menulis, UnifiedSearch membaca

## Error Codes

| Prefix | Tool |
|--------|------|
| IDX_001 | Missing repo_path |
| IDX_002 | Missing schedule params |
| IDX_500 | Internal indexing error |

## Related Sub-Features

- [UnifiedSearch Concept](../unified-search/concept.md)

---

*This document follows CODDY Codeworks documentation standards.*
