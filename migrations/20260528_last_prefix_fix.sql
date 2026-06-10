-- Migration: Fix non-time-based last_ prefix columns
-- Date: 2026-05-28
-- Description: Remove last_ prefix from non-time-based columns
-- Rollback: Reverse all ALTER TABLE statements

-- Phase 1: manifest_entries table
ALTER TABLE manifest_entries ADD COLUMN hash TEXT;
UPDATE manifest_entries SET hash = last_hash WHERE last_hash IS NOT NULL;
ALTER TABLE manifest_entries DROP COLUMN last_hash;

ALTER TABLE manifest_entries ADD COLUMN mtime TEXT;
UPDATE manifest_entries SET mtime = last_mtime WHERE last_mtime IS NOT NULL;
ALTER TABLE manifest_entries DROP COLUMN last_mtime;
