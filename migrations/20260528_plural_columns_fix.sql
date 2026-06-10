-- Migration: Fix non-quantity plural column names
-- Date: 2026-05-28
-- Description: Rename plural columns that don't represent quantities to singular
-- Rollback: Reverse all ALTER TABLE statements

-- Phase 1: commits table
ALTER TABLE commits ADD COLUMN parent_hash TEXT;
UPDATE commits SET parent_hash = parent_hashes WHERE parent_hashes IS NOT NULL;
ALTER TABLE commits DROP COLUMN parent_hashes;

-- Phase 2: devices table
ALTER TABLE devices ADD COLUMN operating_system TEXT;
UPDATE devices SET operating_system = os WHERE os IS NOT NULL;
ALTER TABLE devices DROP COLUMN os;

-- Phase 3: knowledge_chunks table
ALTER TABLE knowledge_chunks ADD COLUMN concept TEXT;
UPDATE knowledge_chunks SET concept = concepts WHERE concepts IS NOT NULL;
ALTER TABLE knowledge_chunks DROP COLUMN concepts;

ALTER TABLE knowledge_chunks ADD COLUMN related_module TEXT;
UPDATE knowledge_chunks SET related_module = related_modules WHERE related_modules IS NOT NULL;
ALTER TABLE knowledge_chunks DROP COLUMN related_modules;

ALTER TABLE knowledge_chunks ADD COLUMN architecture_tag TEXT;
UPDATE knowledge_chunks SET architecture_tag = architecture_tags WHERE architecture_tags IS NOT NULL;
ALTER TABLE knowledge_chunks DROP COLUMN architecture_tags;
