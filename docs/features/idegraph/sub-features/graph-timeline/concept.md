# Graph Timeline

**Purpose:** Model AI conversation memories as a connected graph with historical timeline, project state context, and digital artifact tracking

**Why It Exists:** Current engrams are isolated records. AI coders need to understand the **chronological progression** of ideas, see **where solutions originated**, track **which conversations continued from others**, and identify **what code artifacts were produced** and where they're used.

## Problem Statement

The current flat `Engram` model has these limitations:

- **No temporal graph:** Conversations exist in isolation — no "before/after", "parent/child", or "inspired by" relationships
- **No state capture:** Git branch, commit hash, modified files at conversation time are lost
- **No artifact lifecycle:** Code solutions produced in conversations are buried in messages, not tracked as reusable artifacts
- **No usage tracking:** Can't trace if an idea from conversation A was applied in conversation B
- **Weak project linkage:** workspace_key is a hash without actual repository path integration

## Theoretical Foundation

- **Temporal Graph:** Each engram is a node; edges represent temporal and causal relationships
- **Event Sourcing:** Project states are immutable snapshots captured at conversation start/end
- **Artifact Registry:** Digital artifacts (code solutions, configs) have their own lifecycle independent of conversations
- **Knowledge Graph:** Link artifacts to usage sites (files, commits, later conversations)
- **Hierarchical Time:** Day → Session → Conversation → Message (nested temporal scopes)

## New Domain Entities

### 1. `ConversationGraph` — The Timeline Graph

```python
@dataclass
class ConversationGraph:
    """Graph structure connecting all engrams for a workspace."""
    workspace_key: str
    nodes: List[EngramNode]          # All conversations as graph nodes
    edges: List[ConversationEdge]    # Temporal and causal relationships
    head_node_id: Optional[str]      # Most recent conversation

@dataclass
class EngramNode:
    """Graph-wrapped engram with positional and relational metadata."""
    engram: Engram
    depth: int                       # Graph depth from root (0 = first)
    lineage: List[str]               # IDs of ancestor conversations
    branch_name: Optional[str]       # Named branch of conversation flow
    session_id: str                  # Groups conversations within a single IDE session
    day_bucket: str                  # "2026-05-29" for fast date queries

@dataclass
class ConversationEdge:
    """Typed edge between two engram nodes."""
    source_id: str                   # From conversation
    target_id: str                   # To conversation
    edge_type: EdgeType              # Classification
    confidence: float                # 0.0-1.0, ML-detected vs explicit
    metadata: Dict[str, Any]

class EdgeType(Enum):
    CONTINUES_FROM = "continues_from"     # Same session, natural continuation
    FORKED_FROM = "forked_from"          # Branched to new topic
    REFERENCES = "references"            # Mentions or links to prior conversation
    SAME_SESSION = "same_session"         # Within same IDE session
    SAME_TOPIC = "same_topic"            # Similar keywords/title (ML-detected)
    HAS_ARTIFACT = "has_artifact"        # Produces digital artifact
    USES_ARTIFACT = "uses_artifact"      # Consumes digital artifact
```

### 2. `ProjectState` — Immutable Context Snapshot

```python
@dataclass
class ProjectState:
    """Captures the exact state of a project when a conversation occurred."""
    id: str                          # state_<engram_id>_<timestamp>
    engram_id: str                   # The conversation this state belongs to
    captured_at: datetime

    # Git context
    git_branch: Optional[str]
    git_commit: Optional[str]
    git_commit_message: Optional[str]
    git_dirty_files: List[str]      # Files modified but not committed

    # Workspace context
    repo_path: Optional[str]         # Absolute path to repository root
    repo_remote_url: Optional[str]   # e.g. github.com/user/repo
    repo_id: Optional[str]          # Links to CodeRepository domain

    # File context
    open_files: List[str]           # Files open in IDE at conversation start
    active_file: Optional[str]       # File user was editing
    file_line_count: Dict[str, int] # Line counts per file (size context)

    # Environment
    ide_name: str
    ide_version: Optional[str]
    os_name: Optional[str]
    python_version: Optional[str]  # For Python projects
    node_version: Optional[str]      # For JS/TS projects

@dataclass
class StateTransition:
    """Captures what changed between two consecutive conversations."""
    from_state_id: str
    to_state_id: str
    files_added: List[str]
    files_deleted: List[str]
    files_modified: List[str]
    lines_changed: int
    branch_changed: bool
    commit_distance: int            # Commits between states
```

### 3. `DigitalArtifact` — Extracted Reusable Knowledge

```python
@dataclass
class DigitalArtifact:
    """A code solution, config, or knowledge extracted from a conversation."""
    id: str
    artifact_type: ArtifactType
    engram_id: str                  # Source conversation
    title: str                      # Human-readable name
    description: str                # What it does / why it exists
    content: str                    # The actual code/text
    language: Optional[str]         # python, javascript, json, etc.
    created_at: datetime

    # Context
    file_path: Optional[str]        # Where it should live in project
    target_function: Optional[str]  # Function/class it modifies
    imports_required: List[str]      # Required imports
    dependencies: List[str]          # External packages needed

    # Quality
    confidence: float               # Extraction confidence (ML)
    verified: bool                 # Did user confirm it works?
    tests_pass: Optional[bool]      # Auto-run tests?

class ArtifactType(Enum):
    CODE_SOLUTION = "code_solution"       # Complete code block
    CONFIG_CHANGE = "config_change"       # Settings, env vars
    BUGFIX = "bugfix"                     # Specific fix for issue
    REFACTOR = "refactor"                 # Code restructuring
    ARCHITECTURE_DECISION = "architecture" # ADR-style decision
    LEARNED_PATTERN = "pattern"            # Reusable pattern/rule
    DEBUG_TECHNIQUE = "debug"             # How to diagnose similar issue
    COMMAND = "command"                   # CLI command that solved issue
    WORKFLOW = "workflow"                 # Multi-step process
    DATA_MODEL = "data_model"            # Schema, model definition
    API_SPEC = "api_spec"                # Endpoint, interface definition

@dataclass
class ArtifactUsage:
    """Tracks where an artifact was applied or referenced."""
    artifact_id: str
    usage_type: UsageType
    target_id: str                  # Engram or file ID
    target_path: Optional[str]       # File path where applied
    applied_at: Optional[datetime] # When it was used
    success: Optional[bool]         # Did application succeed?
    diff_preview: Optional[str]     # Unified diff of application

class UsageType(Enum):
    APPLIED_IN_PROJECT = "applied_in_project"    # Code committed to repo
    REFERENCED_IN_CONVERSATION = "referenced"      # Mentioned in later chat
    COPIED_TO_CLIPBOARD = "copied"                 # User copied it
    MODIFIED_AND_REUSED = "modified"               # Changed before using
    REJECTED = "rejected"                          # User discarded it
    DEFERRED = "deferred"                          # Marked for later
```

## Graph Operations

### Timeline Construction

```
build_timeline(workspace_key) → ConversationGraph
1. Fetch all engrams for workspace, sorted by created_at ASC
2. Create EngramNode for each, computing depth and lineage
3. Detect edges:
   a. CONTINUES_FROM: same session, time gap < 30 min
   b. SAME_SESSION: explicit session_id match
   c. SAME_TOPIC: cosine similarity > 0.8 on title+first_message
   d. REFERENCES: explicit "see conversation X" or "like we did in Y"
   e. FORKED_FROM: user starts new conv on related but different topic
4. Compute day_bucket for each node
5. Identify head_node (most recent)
```

### State Capture

```
capture_state(engram_id) → ProjectState
1. Read .git/HEAD for branch
2. Read git log -1 for commit
3. git status --porcelain for dirty files
4. Query IDE API (if available) for open_files, active_file
5. Detect project type (Python: requirements.txt, Node: package.json, etc.)
6. Persist as immutable ProjectState record
```

### Artifact Extraction

```
extract_artifacts(engram_id) → List[DigitalArtifact]
1. Scan messages for code blocks (```...```)
2. Classify each block by ArtifactType (heuristic + ML)
3. Generate title and description via LLM summarization
4. Compute language from file extension or syntax
5. If diffs present in messages, parse as CODE_SOLUTION or BUGFIX
6. Store with engram_id reference and confidence score
```

### Artifact Usage Tracking

```
track_usage(artifact_id, usage_type, target_id, ...)
1. Create ArtifactUsage record
2. If APPLIED_IN_PROJECT:
   a. Capture git diff of application
   b. Link to commit hash if committed
   c. Set success = (no test failures, no compile errors)
3. Update DigitalArtifact.verified if success=True
```

## Graph Visualization Model

```
Day: 2026-05-29
├── Session: cursor-afternoon
│   ├── [Node: engram-001] "Fix auth bug"
│   │   ├── State: branch=feature/auth, commit=abc123, dirty=[auth.py, test_auth.py]
│   │   └── Artifacts:
│   │       ├── [Artifact: art-001] BUGFIX: JWT validation
│   │       └── [Artifact: art-002] CONFIG: env vars
│   │
│   ├── [Node: engram-002] "Add OAuth2" ← CONTINUES_FROM engram-001
│   │   ├── State: branch=feature/auth, commit=def456, dirty=[oauth.py]
│   │   └── Artifacts:
│   │       └── [Artifact: art-003] CODE_SOLUTION: Google OAuth
│   │
│   └── [Node: engram-003] "Debug token refresh" ← REFERENCES engram-001
│       ├── State: branch=feature/auth, commit=ghi789
│       └── Artifacts:
│           └── [Artifact: art-004] DEBUG: Race condition fix
│
├── Session: trae-evening
│   └── [Node: engram-004] "Setup database" ← FORKED_FROM (new topic)
│       └── Artifacts:
│           └── [Artifact: art-005] CONFIG: PostgreSQL setup
│
└── Cross-Reference: art-001
    └── [Usage: u-001] APPLIED_IN_CONVERSATION → engram-003 (referenced fix)
    └── [Usage: u-002] APPLIED_IN_PROJECT → commit=jkl012 (committed to repo)
```

## SQL Schema Additions

```sql
-- Conversation graph edges
CREATE TABLE conversation_edges (
    id TEXT PRIMARY KEY,
    source_engram_id TEXT NOT NULL REFERENCES conversations(id),
    target_engram_id TEXT NOT NULL REFERENCES conversations(id),
    edge_type TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    metadata_json TEXT,
    detected_at TEXT,
    UNIQUE(source_engram_id, target_engram_id, edge_type)
);

-- Project state snapshots
CREATE TABLE project_states (
    id TEXT PRIMARY KEY,
    engram_id TEXT NOT NULL UNIQUE REFERENCES conversations(id),
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

-- State transitions between consecutive conversations
CREATE TABLE state_transitions (
    id TEXT PRIMARY KEY,
    from_state_id TEXT NOT NULL REFERENCES project_states(id),
    to_state_id TEXT NOT NULL REFERENCES project_states(id),
    files_added_json TEXT,
    files_deleted_json TEXT,
    files_modified_json TEXT,
    lines_changed INTEGER,
    branch_changed BOOLEAN,
    commit_distance INTEGER
);

-- Digital artifacts extracted from conversations
CREATE TABLE digital_artifacts (
    id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    engram_id TEXT NOT NULL REFERENCES conversations(id),
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

-- Artifact usage tracking
CREATE TABLE artifact_usage (
    id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL REFERENCES digital_artifacts(id),
    usage_type TEXT NOT NULL,
    target_engram_id TEXT REFERENCES conversations(id),
    target_file_path TEXT,
    target_commit_hash TEXT,
    applied_at TEXT,
    success BOOLEAN,
    diff_preview TEXT,
    created_at TEXT
);

-- Graph traversal index
CREATE INDEX idx_edges_source ON conversation_edges(source_engram_id);
CREATE INDEX idx_edges_target ON conversation_edges(target_engram_id);
CREATE INDEX idx_edges_type ON conversation_edges(edge_type);
CREATE INDEX idx_artifacts_engram ON digital_artifacts(engram_id);
CREATE INDEX idx_artifacts_type ON digital_artifacts(artifact_type);
CREATE INDEX idx_usage_artifact ON artifact_usage(artifact_id);
```

## New MCP Tool Actions

| Action | Purpose |
|--------|---------|
| `timeline` | Get chronological graph for workspace |
| `state` | Get project state snapshot for engram |
| `artifacts` | List digital artifacts for workspace/engram |
| `artifact_get` | Get single artifact by ID |
| `artifact_usage` | Track where artifact was used |
| `related` | Find conversations related to given engram |
| `branch` | Get conversation branch (session lineage) |
| `diff` | Compare states between two engrams |

## AI Coder Impact

| Feature | Token Impact | Value |
|---------|-------------|-------|
| Timeline graph | +200 tokens/response | High — shows context of conversation |
| State snapshots | +150 tokens/response | High — links code to repo state |
| Artifact registry | +100 tokens/item | Very High — reusable solutions |
| Usage tracking | +50 tokens/usage | Medium — proves value |
| Graph traversal | Saves 2-3 tool calls | Very High — follows chains naturally |

## Migration Path

1. **Phase 1:** Add new tables, populate from existing data
2. **Phase 2:** Build timeline for historical conversations
3. **Phase 3:** Start capturing ProjectState on new ingestions
4. **Phase 4:** Enable artifact extraction on compaction
5. **Phase 5:** Track artifact usage via IDE plugins
