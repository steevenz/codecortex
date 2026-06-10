-- Migration: 20260529_graph_cache_hash_and_undo_log
-- Adds repo_hash column for incremental build auto-invalidation
-- Adds refactor_undo_log table for graph_refactor undo support

-- 1. Add repo_hash column to graph_cache (safe: no-op if column already exists)
ALTER TABLE graph_cache ADD COLUMN repo_hash TEXT;

-- 2. Create refactor undo log table
CREATE TABLE IF NOT EXISTS refactor_undo_log (
    id           TEXT PRIMARY KEY,
    target_node  TEXT NOT NULL,
    refactor_type TEXT NOT NULL,
    changes      TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
