-- Migration: Graph Timeline — Conversation graph, project state, digital artifacts
-- Date: 2026-05-29

-- Conversation graph edges (temporal and causal relationships between conversations)
CREATE TABLE IF NOT EXISTS conversation_edges (
    id TEXT PRIMARY KEY,
    source_engram_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    target_engram_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL CHECK(edge_type IN (
        'continues_from', 'forked_from', 'references',
        'same_session', 'same_topic', 'has_artifact', 'uses_artifact'
    )),
    confidence REAL DEFAULT 1.0 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    metadata_json TEXT,
    detected_at TEXT,
    UNIQUE(source_engram_id, target_engram_id, edge_type)
);

-- Graph traversal indexes
CREATE INDEX IF NOT EXISTS idx_edges_source ON conversation_edges(source_engram_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON conversation_edges(target_engram_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON conversation_edges(edge_type);

-- Project state snapshots (immutable context when conversation occurred)
CREATE TABLE IF NOT EXISTS project_states (
    id TEXT PRIMARY KEY,
    engram_id TEXT NOT NULL UNIQUE REFERENCES conversations(id) ON DELETE CASCADE,
    captured_at TEXT NOT NULL,
    git_branch TEXT,
    git_commit TEXT,
    git_commit_message TEXT,
    git_dirty_files_json TEXT,
    repo_path TEXT,
    repo_remote_url TEXT,
    repo_id TEXT,
    open_files_json TEXT,
    active_file TEXT,
    file_stats_json TEXT,
    ide_name TEXT,
    ide_version TEXT,
    os_name TEXT,
    language_versions_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_project_states_engram ON project_states(engram_id);
CREATE INDEX IF NOT EXISTS idx_project_states_repo ON project_states(repo_id);

-- State transitions between consecutive conversations
CREATE TABLE IF NOT EXISTS state_transitions (
    id TEXT PRIMARY KEY,
    from_state_id TEXT NOT NULL REFERENCES project_states(id) ON DELETE CASCADE,
    to_state_id TEXT NOT NULL REFERENCES project_states(id) ON DELETE CASCADE,
    files_added_json TEXT,
    files_deleted_json TEXT,
    files_modified_json TEXT,
    lines_changed INTEGER DEFAULT 0,
    branch_changed BOOLEAN DEFAULT FALSE,
    commit_distance INTEGER DEFAULT 0,
    UNIQUE(from_state_id, to_state_id)
);

-- Digital artifacts extracted from conversations
CREATE TABLE IF NOT EXISTS digital_artifacts (
    id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL CHECK(artifact_type IN (
        'code_solution', 'config_change', 'bugfix', 'refactor',
        'architecture', 'pattern', 'debug', 'command',
        'workflow', 'data_model', 'api_spec'
    )),
    engram_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    title TEXT,
    description TEXT,
    content TEXT,
    language TEXT,
    file_path TEXT,
    target_function TEXT,
    imports_required_json TEXT,
    dependencies_json TEXT,
    confidence REAL DEFAULT 0.0,
    verified BOOLEAN DEFAULT FALSE,
    tests_pass BOOLEAN,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_artifacts_engram ON digital_artifacts(engram_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON digital_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_verified ON digital_artifacts(verified);

-- Artifact usage tracking
CREATE TABLE IF NOT EXISTS artifact_usage (
    id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL REFERENCES digital_artifacts(id) ON DELETE CASCADE,
    usage_type TEXT NOT NULL CHECK(usage_type IN (
        'applied_in_project', 'referenced', 'copied',
        'modified', 'rejected', 'deferred'
    )),
    target_engram_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    target_file_path TEXT,
    target_commit_hash TEXT,
    applied_at TEXT,
    success BOOLEAN,
    diff_preview TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_usage_artifact ON artifact_usage(artifact_id);
CREATE INDEX IF NOT EXISTS idx_usage_target ON artifact_usage(target_engram_id);
CREATE INDEX IF NOT EXISTS idx_usage_type ON artifact_usage(usage_type);
