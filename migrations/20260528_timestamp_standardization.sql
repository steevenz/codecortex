-- Migration: Standardize timestamp columns to sync_at pattern
-- Date: 2026-05-28
-- Description: Rename all _synced_at columns to sync_at for consistency
-- Rollback: Reverse all ALTER TABLE statements

-- Phase 1: repo_sync_state table
ALTER TABLE repo_sync_state ADD COLUMN sync_at TEXT;
UPDATE repo_sync_state SET sync_at = tree_synced_at WHERE tree_synced_at IS NOT NULL;
ALTER TABLE repo_sync_state DROP COLUMN tree_synced_at;

ALTER TABLE repo_sync_state ADD COLUMN disk_sync_at TEXT;
UPDATE repo_sync_state SET disk_sync_at = disk_synced_at WHERE disk_synced_at IS NOT NULL;
ALTER TABLE repo_sync_state DROP COLUMN disk_synced_at;

ALTER TABLE repo_sync_state ADD COLUMN audit_sync_at TEXT;
UPDATE repo_sync_state SET audit_sync_at = audit_synced_at WHERE audit_synced_at IS NOT NULL;
ALTER TABLE repo_sync_state DROP COLUMN audit_synced_at;

ALTER TABLE repo_sync_state ADD COLUMN graph_sync_at TEXT;
UPDATE repo_sync_state SET graph_sync_at = graph_synced_at WHERE graph_synced_at IS NOT NULL;
ALTER TABLE repo_sync_state DROP COLUMN graph_synced_at;

ALTER TABLE repo_sync_state ADD COLUMN test_sync_at TEXT;
UPDATE repo_sync_state SET test_sync_at = test_synced_at WHERE test_synced_at IS NOT NULL;
ALTER TABLE repo_sync_state DROP COLUMN test_synced_at;

-- Phase 2: file_tree table
ALTER TABLE file_tree ADD COLUMN sync_at TEXT;
UPDATE file_tree SET sync_at = cached_at WHERE cached_at IS NOT NULL;
ALTER TABLE file_tree DROP COLUMN cached_at;

-- Phase 3: disk_usage table
ALTER TABLE disk_usage ADD COLUMN sync_at TEXT;
UPDATE disk_usage SET sync_at = checked_at WHERE checked_at IS NOT NULL;
ALTER TABLE disk_usage DROP COLUMN checked_at;
