---
name: codecortex-project
description: Use when initializing repositories, inspecting codebase health, running full analysis pipeline, incremental sync, scaffolding greenfield projects, modernizing brownfield legacy code, or managing multi-repo setups via CodeCortex
---

# codecortex:repository + scaffolder — Project Lifecycle

**13 repository actions + 7 scaffolder actions**

**Docs**: `docs/features/coderepository/concept.md` | `docs/features/scaffolder/concept.md`

**Workflows**: `docs/workflows/greenfield-workflow.md` (WFK_GRN) | `docs/workflows/brownfield-workflow.md` (WFK_LGY)
| `docs/workflows/multi-repo-workflow.md` (WFK_MRP) | `docs/workflows/mono-repo-workflow.md` (WFK_MNR)

---

## Repository Tool: `codecortex:repository`

### action: init — Initialize Repository (WFK_GRN_001 Phase 1-2)

```
action: init
args: {vcs_type:"git", remote_url?, force?, run_audit:true, parallel:true, max_workers:4}
```

Returns `{repo_id, repo_path, vcs_type, indexing_summary}`.

**First call** before any other tool. Save `repo_id` for all subsequent calls.

If `409` response: repo already exists. Use returned `existing_repo_id`.

---

### action: inspect — Fast Health Check (WFK_ANA_001 Phase 1)

```
action: inspect
args: {include_git_diagnostics:true, include_index_metadata:true, include_file_stats:true, include_dependency_summary:true, timeout:30}
```

**Zero parsing** — instant. Returns `ai_readiness_score`:

| Score | Meaning | Action |
|-------|---------|--------|
| < 50 | Needs full index | Run `init` + `analyze` |
| 50-69 | Partially indexed | Run `analyze` incremental |
| ≥ 70 | Healthy | Skip to `cb:status` |

Also returns `git_diagnostics.{churn_hotspots, bus_factor, bug_magnets, commit_velocity}`.

---

### action: analyze — Full 7-Phase Pipeline (WFK_ANA_001 Phase 2)

```
action: analyze
args: {force:?, incremental:true, build_graph:true, extract_symbols:true,
       store_embeddings:?, languages?, parallel:true, timeout:300, dry_run:?}
```

Phases: discovery → indexing → graph → embeddings → VCS → complexity → codemap.

Use `dry_run:true` to preview without DB mutations.

**Token economy**: Incremental sync saves ~90% tokens on re-index via git-diff.

---

### action: sync — Incremental Re-sync (WFK_SYN_001)

```
action: sync
args: {mode:"auto", reindex_updated:true, remove_deleted:true, dry_run:?}
```

git-diff based. Only changed files re-parsed. Call periodically for cached repos.

---

### Other Repository Actions

| action | Purpose | Key Args |
|--------|---------|----------|
| `audit` | Git history + secrets scan | `secrets:true, include_git_history:true` |
| `staleness` | Check if index stale | `compare_remote:true` |
| `list` | All registered repos | `filter_status:"all", limit:50` |
| `compact` | VACUUM + export snapshot | `compact_db:true, output_format:"yaml"` |
| `cleanup` | **Delete ALL repo data** | `force:?` — irreversible |
| `dump` | Export to portable YAML/JSON | `format:"yaml", output_dir:?` |
| `restore` | Import from dump | `source:, overwrite:?` |
| `git` | Arbitrary git | `subcommand:, args:, flags:` |
| `svn` | SVN operations | `target:, subcommand:, args:` |

---

## Scaffolder Tool: `codecortex:scaffolder` (WFK_GRN_001-003)

See: `docs/workflows/greenfield-workflow.md` | `docs/features/scaffolder/concept.md`

### Workflow
```
1. list_stacks            → see available stacks (14+ languages)
2. get_stack stack_name:   → details per stack
3. validate_name name:     → normalize project name
4. create_project          → full scaffold with dry_run:true first
```

### action: create_project
```
args: {name:, stack:"python", project_type:"standard", target_path:, author:,
       email:, version:"0.1.0", license:"MIT", dry_run:true, overwrite:false}
```

**Stacks**: python, typescript, javascript, go, java, kotlin, c#, swift, rust, c++, dart, flutter, php

**Project types per stack**: standard, web_api, cli_tool, data_science, automation, etc.

### action: generate_class — 28 Code Types
```
args: {type:"model|service|controller|repository|dto|value_object|event|listener|job|middleware|factory|seeder|migration|enum|trait|helper|validator|mapper|interface|abstract|...",
       name:, stack:"python", module:, target_path:, overwrite:false}
```

### action: generate_content — 6 File Types
```
args: {file_type:"gitignore|env|pyproject|readme|requirements|dockerfile", project_name:, author:, email:, license_name:"MIT"}
```

---

## Brownfield Workflows (WFK_LGY_001-005)

See: `docs/workflows/brownfield-workflow.md`

| Code | Purpose | Pipeline |
|------|---------|----------|
| WFK_LGY_001 | Knowledge Graph Construction | init → analyze → graph build → kg extract → idegraph ingest |
| WFK_LGY_002 | Safe Feature Addition | impact analysis → add → test → verify |
| WFK_LGY_003 | Incremental Modernization | audit → refactor → test → sync |
| WFK_LGY_004 | Strangler Fig Migration | identify bounded context → route extraction → parallel implementation |
| WFK_LGY_005 | Service Extraction | modularize → community detection → extract |

---

## Multi-Repo Workflow (WFK_MRP_001)

See: `docs/workflows/multi-repo-workflow.md`

```
1. repo init <path1> → repo_id_1
2. repo init <path2> → repo_id_2
3. repo analyze <path1> + repo analyze <path2>  (parallel)
4. cb search across repos via repo_id
```

Up to **50 repos** per CodeCortex instance.

---

## Staleness Detection

Run `staleness` before analysis on previously-indexed repos. If `stale_files > 0`, run `sync`.

---

## Feature Docs per Action

| Domain | Concept | Lifecycle Example | AI-Impact |
|--------|---------|-------------------|-----------|
| CodeRepository | `docs/features/coderepository/concept.md` | `docs/features/coderepository/examples/lifecycle-workflow.md` | `docs/features/coderepository/ai-impact-token-efficiency.md` |
| Scaffolder | `docs/features/scaffolder/concept.md` | `docs/features/scaffolder/examples/create-project.json` | `docs/features/scaffolder/ai-impact-token-efficiency.md` |

---

## CLI Equivalents

See `docs/guides/how-to-use-cli.md`:

```bash
codecortex repo init /path/to/project
codecortex repo inspect /path/to/project --include-git-diagnostics
codecortex repo analyze /path/to/project --build-graph
codecortex repo sync /path/to/project
codecortex scaffold create --name MyProject --stack python --dry-run
```
