# IDEGraph Graph Timeline — Architecture & Design

**Date:** 2026-05-29
**Status:** Design Complete, Domain Model Implemented
**Scope:** Historical conversation graph, project state snapshots, digital artifact tracking

---

## Problem Analysis

The current `Engram` model stores conversations as flat, isolated records. Missing capabilities:

1. **No temporal graph** — Can't trace "before/after", "inspired by", "continued from" relationships
2. **No state capture** — Git branch, commit, modified files at conversation time are lost
3. **No artifact lifecycle** — Code solutions are buried in messages, not tracked as reusable artifacts
4. **No usage tracking** — Can't trace if an idea from conversation A was applied in conversation B
5. **Weak repository linkage** — `workspace_key` is a hash without actual repo integration

---

## Solution: 4 New Domain Entities

### 1. `ConversationGraph` — The Timeline Graph

**Nodes:** `EngramNode` wraps each Engram with:
- `depth`: Graph depth from root (0 = first conversation)
- `lineage`: IDs of ancestor conversations (breadcrumb trail)
- `session_id`: Groups conversations within a single IDE session
- `day_bucket`: Fast date-based queries (e.g. "2026-05-29")

**Edges:** `ConversationEdge` with types:
- `CONTINUES_FROM`: Same session, <30 min gap (confidence: 1.0)
- `SAME_SESSION`: Same IDE session but longer gap (confidence: 0.9)
- `SAME_TOPIC`: Similar title/content via SequenceMatcher (confidence: 0.7-0.99)
- `FORKED_FROM`: Branched to new topic (explicit or ML-detected)
- `REFERENCES`: Explicit mention of prior conversation
- `HAS_ARTIFACT`: Produces digital artifact
- `USES_ARTIFACT`: Consumes digital artifact

**Graph Operations:**
- `get_timeline(engram_id)` → Chronological path from root to target
- `get_related(engram_id)` → All connected conversations via edges
- `get_branch(session_id)` → All conversations in a session
- `get_day_summary(day)` → Daily activity summary

### 2. `ProjectState` — Immutable Context Snapshot

Captures the exact project state when a conversation started:

```
ProjectState
├── Git Context
│   ├── git_branch      # e.g. "feature/auth"
│   ├── git_commit      # e.g. "abc123..."
│   ├── git_commit_message
│   └── git_dirty_files # ["auth.py", "test_auth.py"]
├── Workspace Context
│   ├── repo_path       # /home/user/projects/myapp
│   ├── repo_remote_url # github.com/user/repo
│   └── repo_id         # Links to CodeRepository domain
├── File Context
│   ├── open_files      # ["auth.py", "models.py"]
│   ├── active_file     # "auth.py"
│   └── file_line_count # {"auth.py": 150, "models.py": 80}
└── Environment
    ├── ide_name        # "cursor"
    ├── ide_version     # "0.45.0"
    ├── os_name         # "Windows 11"
    ├── python_version  # "3.12.0"
    └── node_version    # "20.0.0"
```

**StateTransition** captures changes between consecutive conversations:
- files_added, files_deleted, files_modified
- lines_changed, branch_changed, commit_distance

### 3. `DigitalArtifact` — Extracted Reusable Knowledge

A code solution, config, or pattern extracted from conversation messages:

```
DigitalArtifact
├── Core
│   ├── artifact_type   # code_solution, bugfix, config_change, etc.
│   ├── title           # "JWT Validation Fix"
│   ├── description     # "Validates JWT tokens with proper expiry check"
│   ├── content         # The actual code
│   └── language        # "python"
├── Context
│   ├── file_path       # Where it should live: "src/auth/jwt.py"
│   ├── target_function # "validate_token"
│   ├── imports_required # ["jwt", "datetime"]
│   └── dependencies    # ["PyJWT>=2.0"]
└── Quality
    ├── confidence      # 0.0-1.0 (extraction confidence)
    ├── verified        # Did user confirm it works?
    └── tests_pass      # Auto-run test results
```

**Artifact Types:**
- `CODE_SOLUTION` — Complete code block
- `BUGFIX` — Specific fix for an issue
- `CONFIG_CHANGE` — Settings, env vars
- `REFACTOR` — Code restructuring
- `ARCHITECTURE_DECISION` — ADR-style decision
- `LEARNED_PATTERN` — Reusable pattern
- `DEBUG_TECHNIQUE` — How to diagnose similar issues
- `COMMAND` — CLI command that solved issue
- `WORKFLOW` — Multi-step process
- `DATA_MODEL` — Schema, model definition
- `API_SPEC` — Endpoint, interface definition

### 4. `ArtifactUsage` — Usage Tracking

Tracks where artifacts were applied:

```
ArtifactUsage
├── artifact_id     # Which artifact
├── usage_type      # applied_in_project, referenced, copied, etc.
├── target_engram_id # Conversation that used it
├── target_file_path # File where applied
├── target_commit_hash # Git commit hash
├── applied_at      # When it was used
├── success         # Did application succeed?
└── diff_preview    # Unified diff of changes
```

---

## Implementation

### Files Created

| File | Purpose |
|------|---------|
| `docs/features/idegraph/sub-features/graph-timeline/concept.md` | Design specification |
| `src/modules/idegraph/domain/graph.py` | Domain model (320+ lines) |
| `src/modules/idegraph/services/graph_builder.py` | Graph construction service |
| `migrations/20260529_graph_timeline.sql` | Schema additions (5 tables, 7 indexes) |

### Files Modified

| File | Changes |
|------|---------|
| `docs/features/idegraph/concept.md` | Architecture diagram, 10/10 features, sub-features list |

### Domain Model Stats

| Entity | Fields | Methods |
|--------|--------|---------|
| `ConversationEdge` | 6 | `to_dict()`, `from_dict()` |
| `EngramNode` | 7 | `to_dict()`, `id` property |
| `ProjectState` | 17 | `to_dict()`, `from_dict()` |
| `StateTransition` | 8 | `to_dict()` |
| `DigitalArtifact` | 14 | `to_dict()`, `from_dict()` |
| `ArtifactUsage` | 9 | `to_dict()` |
| `ConversationGraph` | 4 | `get_node()`, `get_related()`, `get_timeline()`, `get_branch()`, `get_day_summary()` |

### Graph Builder Algorithm

```
build_timeline(engrams, workspace_key)
1. Sort engrams by created_at ASC
2. For each engram:
   a. Compute session_id: "{ide}:{YYYYmmddHH}"
   b. Compute depth from predecessor (if same session & <30 min gap)
   c. Build lineage breadcrumb
   d. Create EngramNode
3. Detect edges (O(n²) pairwise comparison):
   a. SAME_SESSION: explicit session match
   b. CONTINUES_FROM: same session + <30 min gap
   c. SAME_TOPIC: SequenceMatcher ratio > 0.7
4. Return ConversationGraph
```

---

## SQL Schema Additions

### New Tables (5)

1. **conversation_edges** — Graph edges between conversations
   - PK: `id`
   - FK: `source_engram_id → conversations(id)`
   - FK: `target_engram_id → conversations(id)`
   - Fields: `edge_type`, `confidence`, `metadata_json`, `detected_at`
   - Unique: `(source, target, type)`

2. **project_states** — Immutable state snapshots
   - PK: `id`
   - FK: `engram_id → conversations(id)` UNIQUE
   - Fields: git info, repo info, file context, environment

3. **state_transitions** — Changes between consecutive states
   - PK: `id`
   - FK: `from_state_id → project_states(id)`
   - FK: `to_state_id → project_states(id)`
   - Fields: files changed, lines changed, branch/commit distance

4. **digital_artifacts** — Extracted reusable knowledge
   - PK: `id`
   - FK: `engram_id → conversations(id)`
   - Fields: type, title, content, language, file path, quality metrics

5. **artifact_usage** — Where artifacts were applied
   - PK: `id`
   - FK: `artifact_id → digital_artifacts(id)`
   - FK: `target_engram_id → conversations(id)` nullable
   - Fields: usage_type, file path, commit hash, success, diff

### New Indexes (7)

- `idx_edges_source` — Fast source traversal
- `idx_edges_target` — Fast target traversal
- `idx_edges_type` — Filter by edge type
- `idx_project_states_engram` — Lookup state by conversation
- `idx_artifacts_engram` — Find artifacts by source conversation
- `idx_artifacts_type` — Filter by artifact type
- `idx_usage_artifact` — Find usages by artifact

---

## MCP Tool Actions (Proposed)

| Action | Description |
|--------|-------------|
| `timeline` | Get chronological graph for workspace |
| `state` | Get project state snapshot for engram |
| `artifacts` | List digital artifacts for workspace/engram |
| `artifact_get` | Get single artifact by ID |
| `artifact_usage` | Track where artifact was used |
| `related` | Find conversations related to given engram |
| `branch` | Get conversation branch (session lineage) |
| `diff` | Compare states between two engrams |

---

## Token Impact Analysis

| Feature | Token Cost | AI Value |
|---------|-----------|----------|
| Timeline graph | +200 tokens/response | Very High — shows conversation context |
| State snapshots | +150 tokens/response | Very High — links code to repo state |
| Artifact registry | +100 tokens/item | Very High — reusable solutions |
| Usage tracking | +50 tokens/usage | Medium — proves value |
| Graph traversal | Saves 2-3 tool calls | Very High — follows chains naturally |

---

## Migration Path

1. **Phase 1 (Now):** Schema deployed, domain model ready
2. **Phase 2:** Build timeline for historical conversations on ingest
3. **Phase 3:** Start capturing ProjectState on new ingestions
4. **Phase 4:** Enable artifact extraction during compaction
5. **Phase 5:** Track artifact usage via IDE plugins/API

---

## Summary

The graph timeline feature transforms idegraph from a **flat conversation log** into a **rich knowledge graph** that understands:

- **When** conversations happened (temporal ordering)
- **How** they're connected (continues, forks, references)
- **What** the project looked like (state snapshots)
- **What** knowledge was produced (artifacts)
- **Where** that knowledge was used (usage tracking)

This makes idegraph production-ready for AI coders who need deep historical context and reusable solutions across their multi-IDE workflow.
