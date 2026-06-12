---
name: codecortex-idegraph
description: Use when searching cross-IDE AI conversation memories, resuming work across sessions, harvesting IDE configs, exploring conversation timelines/lineages, compacting old conversations, or building persistent project context via CodeCortex
---

# codecortex:idegraph — Cross-IDE Memory Network (WFK_IDE_001)

**11 actions**: `search | get | list | ingest | refresh | health | stats | compact | workspace | harvest | export | timeline`

**Tool**: `codecortex:idegraph`

**Docs**: `docs/features/idegraph/concept.md` | `docs/workflows/ide-context-workflow.md` (WFK_IDE_001)

---

## Supported IDEs (16+ Parsers)

Claude Code, Cursor, Windsurf, Cline, Trae, Continue, Codex CLI, Gemini CLI, Copilot CLI, OpenCode, Kimi, Kiro, Kilo, Qwen, Verdent, CodeBuddy, Antigravity

**Per-IDE parsers**: `src/modules/idegraph/parsers/*_parser.py`

---

## action: search — Find Relevant Memories

```
action: search
args: {query:, search_mode:"keyword", search_fields:?, project_name?, ide_name?,
       workspace_key?, date_from:, date_to:, min_messages?, max_messages?,
       limit:20, offset:0, summary_mode:?}
```

**Search modes:**
| Mode | Syntax | Example |
|------|--------|---------|
| `keyword` | Plain text | `auth redesign` |
| `glob` | Path pattern | `src/**` |
| `regex` | `/pattern/` flags | `/auth.*/i` |
| `fuzzy` | `~text~` | `~auth~` |
| `boolean` | AND/OR/NOT | `auth AND oauth NOT facebook` |

**Search fields**: `all`, `title`, `content`, `code`, `diffs`, `tools`, `source`, `project`

**Returns**: `{items[{id, title, source, project_name, score, matched_fields, snippets}], count}`

---

## action: get — Single Memory Detail

```
action: get
args: {memory_id:}
```

Returns full engram: messages, code diffs, tool calls, project state (git branch, commit, open files).

**Token economy**: Use `summary_mode:true` in search to avoid fetching full conversations. ~75-95% savings.

---

## action: list — Browse Memories

```
action: list
args: {project_name?, workspace_key?, ide_name?, limit:20, offset:0, include_engram_count:true}
```

---

## action: ingest — Full Ingestion (WFK_IDE_001 Phase 3)

```
action: ingest
args: (none — auto-detects all IDE sources)
```

Runs ALL IDE parsers and persists results. Call once per session or after installing new IDE.

**Pipeline**: `docs/workflows/ide-context-workflow.md`:
1. `repo init + analyze` → AST index
2. `knowledge extract` → doc knowledge
3. `idegraph ingest` → IDE memories
4. `idegraph search` → verify

---

## action: refresh — Re-ingest Project

```
action: refresh
args: {project_path:}
```

Faster than full `ingest`. Use when a specific project's memory needs updating.

---

## action: harvest — Collect IDE Configs

```
action: harvest
args: {force:false}
```

Harvests IDE configs, settings, extensions, custom prompts from all detected IDEs.

---

## action: compact — Summarize Old Sessions

```
action: compact
args: {limit:100, focus?:}
```

LLM-powered summarization of older conversations. Reduces storage while preserving key:
- Decisions made
- Code solutions discovered
- Bug fixes applied
- Configuration changes

**Example**: `docs/features/idegraph/examples/compact-example.md`

---

## action: timeline — Conversation Lineage

```
action: timeline
args: {workspace_key?, limit:10}
```

Returns chronological view: `{summary, recent_activity[{title, source, depth, relationships}], suggested_context}`.

Fields:
| Field | Meaning |
|-------|---------|
| `depth` | Position in conversation chain (0=start, 1=reply, 2+ = continuation) |
| `ancestors` | Previous conversations in same lineage |
| `related_conversations` | Connected by topic/reason |

**Example**: `docs/features/idegraph/examples/graph-timeline-example.md`

---

## Session Resume Pattern (WFK_IDE_001)

From `docs/workflows/ide-context-workflow.md`:

```
1. idegraph search query:"project-name"   → find previous sessions
2. idegraph get memory_id:"<id>"           → full context + project state
3. repo inspect repo_path:"<path>"         → current codebase state
4. Resume work using context + history
```

### Fresh Start
```
idegraph ingest     → harvest ALL IDE memories
idegraph harvest   → collect IDE configs
```

Search for anything relevant before starting new work.

---

## Timeline Exploration

```
action=search query:"auth redesign" date_from:"2026-01-01" date_to:"2026-06-01"
```

Returns conversations chronologically — trace decision evolution.

**Suggested context**: After getting a memory, check `suggested_context.related_to_latest` and `suggested_context.recent_fixes` for connected conversations.

---

## Token Economy

| Format | Tokens | Use Case |
|--------|--------|----------|
| Full conversation | ~15,000 | Deep debugging |
| `summary_mode:true` | ~500 | Quick overview |
| `related` context | ~1,200 | Deep context |
| **Savings** | **75-95%** vs full dump |

---

## Feature Docs

| Resource | Path |
|----------|------|
| Concept | `docs/features/idegraph/concept.md` |
| AI-Impact | `docs/features/idegraph/ai-impact-token-efficiency.md` |
| Timeline Example | `docs/features/idegraph/examples/graph-timeline-example.md` |
| Compact Example | `docs/features/idegraph/examples/compact-example.md` |
| Ingest Example | `docs/features/idegraph/examples/ingest-example.md` |
| Search Example | `docs/features/idegraph/examples/search-example.md` |
| IDE Context Workflow | `docs/workflows/ide-context-workflow.md` (WFK_IDE_001) |
| Brownfield Workflow | `docs/workflows/brownfield-workflow.md` (WFK_LGY_001) |
