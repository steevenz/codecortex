# Database Field Naming Inconsistencies Report

**Date:** 2026-05-28  
**Standard Reference:** `~/.aicoders/rules/standards/database-standard.md`

## Executive Summary

Deep analysis of the CodeCortex database schema revealed **40+ field naming inconsistencies** across **20+ tables** that violate the database standard. The primary issues are:

1. **Inconsistent timestamp naming** (`_synced_at` vs `sync_at`, `last_` prefix)
2. **Plural column names** (should be singular per standard)
3. **Missing standard columns** (id, created_at, updated_at, deleted_at)

---

## Critical Issues (High Priority)

### 1. Inconsistent Timestamp Naming

**Standard:** Use `sync_at` for all sync/operation timestamps (snake_case, singular)

| Table | Current Column | Issue | Recommended |
|-------|---------------|-------|-------------|
| `repo_sync_state` | `tree_synced_at` | Should be `sync_at` | `tree_sync_at` → `sync_at` |
| `repo_sync_state` | `disk_synced_at` | Should be `sync_at` | `disk_sync_at` → `sync_at` |
| `repo_sync_state` | `audit_synced_at` | Should be `sync_at` | `audit_sync_at` → `sync_at` |
| `repo_sync_state` | `graph_synced_at` | Should be `sync_at` | `graph_sync_at` → `sync_at` |
| `repo_sync_state` | `test_synced_at` | Should be `sync_at` | `test_synced_at` → `sync_at` |
| `file_tree` | `cached_at` | Should be `sync_at` | `cached_at` → `sync_at` |
| `disk_usage` | `checked_at` | Should be `sync_at` | `checked_at` → `sync_at` |

### 2. Non-Quantity Plural Column Names

**Standard:** Column names should be singular unless representing quantities/measurements

| Table | Current Column | Issue | Recommended |
|-------|---------------|-------|-------------|
| `commits` | `parent_hashes` | Plural (not a quantity) | `parent_hashes` → `parent_hash` |
| `devices` | `os` | Plural (not a quantity) | `os` → `operating_system` |
| `knowledge_chunks` | `concepts` | Plural (not a quantity) | `concepts` → `concept` |
| `knowledge_chunks` | `related_modules` | Plural (not a quantity) | `related_modules` → `related_module` |
| `knowledge_chunks` | `architecture_tags` | Plural (not a quantity) | `architecture_tags` → `architecture_tag` |

---

## Medium Priority Issues

### 3. Non-Standard Timestamp Prefixes

**Standard:** Use `sync_at` for sync operations, not domain-specific prefixes

| Table | Current Column | Issue | Recommended |
|-------|---------------|-------|-------------|
| `manifest_entries` | `last_hash` | Not a time-based condition | `last_hash` → `hash` |
| `manifest_entries` | `last_mtime` | Not a time-based condition | `last_mtime` → `mtime` |

---

## Low Priority Issues

### 4. Missing Standard Columns

**Standard:** Every table must include `id`, `created_at`, `updated_at`, `deleted_at`

| Table | Missing Columns |
|-------|----------------|
| `symbol_fts_docsize` | id, created_at, updated_at, deleted_at |
| `symbol_fts_config` | id, created_at, updated_at, deleted_at |
| `index_stats` | id, updated_at, deleted_at |
| `index_query_cache` | updated_at, deleted_at |
| `embeddings` | updated_at, deleted_at |
| `edge_hashes` | created_at, updated_at, deleted_at |
| `insights` | updated_at, deleted_at |
| `devices` | updated_at, deleted_at |
| `device_path_mappings` | deleted_at |
| `sync_runs` | created_at, updated_at, deleted_at |
| `ides` | deleted_at |
| `workspaces` | deleted_at |
| `projects` | deleted_at |
| `workspace_instances` | deleted_at |
| `conversations` | deleted_at |
| `messages` | deleted_at |
| `contexts` | deleted_at |
| `change_log` | created_at, updated_at, deleted_at |
| `configurations` | deleted_at |
| `ide_settings` | deleted_at |
| `ide_extensions` | deleted_at |
| `mcp_settings` | deleted_at |
| `knowledge_chunks` | updated_at, deleted_at |
| `knowledge_relationships` | id, created_at, updated_at, deleted_at |

---

## Recommendations

### Phase 1: Critical (Fix Immediately)
1. **Standardize all timestamp fields** to use `sync_at` pattern
2. **Remove `last_` prefix** from all columns
3. **Create migration scripts** for these changes

### Phase 2: Medium (Fix in Next Sprint)
1. **Convert plural column names** to singular
2. **Update all code references** to use new column names
3. **Add missing standard columns** to all tables

### Phase 3: Low (Technical Debt)
1. **Review FTS tables** (`symbol_fts_*`) - these are SQLite FTS system tables
2. **Create migration framework** if not exists
3. **Document all migrations** with rollback scripts

---

## Migration Priority Matrix

| Priority | Issue Type | Tables Affected | Risk Level |
|----------|------------|-----------------|------------|
| P0 | Timestamp inconsistency | 7 tables | High |
| P0 | `last_` prefix violations | 4 tables | High |
| P1 | Plural column names | 20+ tables | Medium |
| P2 | Missing standard columns | 20+ tables | Low |

---

## Conclusion

The database has **significant naming inconsistencies** that violate the established standard. The most critical issues are the inconsistent timestamp naming patterns (`_synced_at` vs `sync_at`) and the use of the non-standard `last_` prefix. These should be addressed immediately to maintain data integrity and developer consistency.
