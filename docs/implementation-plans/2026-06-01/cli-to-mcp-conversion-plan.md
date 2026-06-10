# CLI to MCP Tools Conversion Implementation Plan

**Date**: 2026-06-01  
**Project**: CodeCortex MCP Server  
**Plan Type**: Full CLI to MCP Tools Alignment  
**Status**: Implementation Plan

---

## 1. Executive Summary

This plan outlines the conversion of all CLI commands to follow MCP tools conventions using structured `action` arguments. The goal is to achieve **100% alignment** between CLI interface and MCP tools specification.

### Key Objective
Convert CLI subcommands (e.g., `repository init`, `server start`) into structured `action` arguments (e.g., `repository(action="init")`) to match MCP tools pattern.

---

## 2. Command Alignment Analysis

### 2.1 Current State Mapping

| CLI Command | Current Pattern | MCP Tool | MCP Action | Status |
|-------------|-----------------|----------|------------|--------|
| `repository init` | Subcommand | `codecortex_repository` | `init` | ✅ Convert |
| `repository inspect` | Subcommand | `codecortex_repository` | `inspect` | ✅ Convert |
| `repository analyze` | Subcommand | `codecortex_repository` | `analyze` | ✅ Convert |
| `repository sync` | Subcommand | `codecortex_repository` | `sync` | ✅ Convert |
| `repository audit` | Subcommand | `codecortex_repository` | `audit` | ✅ Convert |
| `repository staleness` | Subcommand | `codecortex_repository` | `staleness` | ✅ Convert |
| `repository list` | Subcommand | `codecortex_repository` | `list` | ✅ Convert |
| `repository compact` | Subcommand | `codecortex_repository` | `compact` | ✅ Convert |
| `repository cleanup` | Subcommand | `codecortex_repository` | `cleanup` | ✅ Convert |
| `repository dump` | Subcommand | `codecortex_repository` | `dump` | ✅ Convert |
| `repository restore` | Subcommand | `codecortex_repository` | `restore` | ✅ Convert |
| `repository git` | Subcommand | `codecortex_repository` | `git` | ✅ Convert |
| `repository svn` | Subcommand | `codecortex_repository` | `svn` | ✅ Convert |

### 2.2 Commands Requiring Conversion

| CLI Domain | Commands to Convert | MCP Tool | MCP Action(s) |
|------------|---------------------|----------|---------------|
| **server** | start, stop, status | `codecortex_repository` | `server_start`, `server_stop`, `server_status` |
| **cloud** | deploy, logs, status | `codecortex_repository` | `cloud_deploy`, `cloud_logs`, `cloud_status` |
| **remote** | path-map, list, unmap, resolve | `codecortex_repository` | `remote_path_map`, `remote_list`, `remote_unmap`, `remote_resolve` |
| **cct** | think-start, analyze, projects, project-add, project-status, code-analyze, code-search | `codecortex_cct` | New unified tool |
| **ai** | analyze | `codecortex_ai` | `analyze` |
| **knowledgegraph** | init, search, list, stats, compact | `knowledge` | `init`, `search`, `list`, `stats`, `compact` |

---

## 3. Naming Convention Standard

### 3.1 CLI Naming Convention (Before → After)

| Current | New Standard | Rationale |
|---------|--------------|-----------|
| `kebab-case` (e.g., `think-start`) | `snake_case` (e.g., `think_start`) | Match MCP tools naming |
| Subcommands (e.g., `repository init`) | Single command with action (e.g., `codecortex_repository(action="init")`) | Unified interface |
| Domain prefixes (e.g., `cct analyze`) | Tool name prefix (e.g., `codecortex_cct(action="analyze")`) | Consistent with MCP |

### 3.2 Action Naming Standard

```
<tool_name>(action="<action_name>", args={...})
```

**Examples:**
- `repository init` → `codecortex_repository(action="init", args={"repo_path": "..."})`
- `server start` → `codecortex_repository(action="server_start", args={"port": 8001})`
- `cct think-start` → `codecortex_cct(action="think_start", args={"problem": "..."})`

---

## 4. Design Conversion Strategy

### 4.1 CLI Parser Refactoring

**Before:**
```python
# src/cli/__init__.py
subparsers.add_parser("repository")
    .add_subparsers(dest="repo_action")
    .add_parser("init")
    .add_parser("analyze")
```

**After:**
```python
# src/cli/__init__.py
subparsers.add_parser("codecortex_repository")
    .add_argument("--action", required=True)
    .add_argument("--args", type=json.loads)
```

### 4.2 Command Router Design

```python
def build_parser(subparsers) -> None:
    # Unified MCP-style tool parsers
    tools = ["codecortex_repository", "codecortex_filesystem", "codecortex_codebase",
             "codecortex_scaffolder", "codecortex_cct", "codecortex_ai",
             "knowledge", "server", "cloud", "remote"]
    
    for tool in tools:
        p = subparsers.add_parser(tool, help=f"{tool} MCP tool")
        p.add_argument("--action", required=True, help="Action to perform")
        p.add_argument("--args", type=str, default="{}", help="JSON args")
        p.add_argument("--repo-path", help="Repository path")
        p.add_argument("--repo-id", help="Repository ID")
```

### 4.3 Backward Compatibility Layer

```python
# Map legacy commands to new format
LEGACY_COMMANDS = {
    "repository init": {"tool": "codecortex_repository", "action": "init"},
    "server start": {"tool": "codecortex_repository", "action": "server_start"},
    "cct think-start": {"tool": "codecortex_cct", "action": "think_start"},
}
```

---

## 5. Implementation Phases

### Phase 1: Foundation (Week 1)

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Create unified CLI parser | 2 days |
| 1.2 | Implement command router | 1 day |
| 1.3 | Add backward compatibility layer | 1 day |
| 1.4 | Update help documentation | 0.5 day |

### Phase 2: Core Tools (Week 2)

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Convert repository commands | 1 day |
| 2.2 | Convert filesystem commands | 1 day |
| 2.3 | Convert codebase commands | 1 day |
| 2.4 | Convert scaffolder commands | 1 day |

### Phase 3: Extended Tools (Week 3)

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Create `codecortex_cct` tool | 1 day |
| 3.2 | Create `codecortex_ai` tool | 0.5 day |
| 3.3 | Create `knowledge` tool | 1 day |
| 3.4 | Add server management commands | 0.5 day |
| 3.5 | Add cloud commands | 1 day |
| 3.6 | Add remote commands | 1 day |

### Phase 4: Testing & Validation (Week 4)

| Task | Description | Effort |
|------|-------------|--------|
| 4.1 | Unit tests for all conversions | 2 days |
| 4.2 | Integration tests | 1 day |
| 4.3 | Edge case testing | 1 day |
| 4.4 | Performance testing | 0.5 day |
| 4.5 | Documentation update | 0.5 day |

---

## 6. Testing Scenarios

### 6.1 Functional Testing

| Test Case | CLI | MCP Equivalent | Expected |
|-----------|-----|----------------|----------|
| Repository init | `codecortex_repository --action init --args '{"repo_path":"..."}'` | `repository(action="init", repo_path="...")` | ✅ Same result |
| File read | `codecortex_filesystem --action read --args '{"path":"..."}'` | `filesystem(action="read", path="...")` | ✅ Same result |
| Code search | `codecortex_codebase --action search --args '{"query":"foo"}'` | `codebase(action="search", query="foo")` | ✅ Same result |
| Server start | `server --action server_start --args '{"port":8001}'` | New tool | ✅ New functionality |

### 6.2 Naming Compatibility Tests

| Test | Description | Expected |
|------|-------------|----------|
| kebab-to-snake | `think-start` → `think_start` | ✅ Converted |
| domain-prefix | `cct analyze` → `codecortex_cct analyze` | ✅ Converted |
| action-arg | `repository init` → `action="init"` | ✅ Converted |

### 6.3 Edge Cases

| Scenario | CLI Input | MCP Input | Expected |
|----------|-----------|-----------|----------|
| Empty args | `--args {}` | `{}` | ✅ No error |
| Large payload | 10MB data | 10MB data | ✅ Truncated |
| Invalid JSON | `--args "invalid"` | N/A | ✅ Error message |
| Missing action | No `--action` | N/A | ✅ Required error |
| Unknown action | `--action unknown` | N/A | ✅ Not found error |

---

## 7. Release Schedule

### Week 1: Foundation
- **Day 1-2**: Unified parser implementation
- **Day 3**: Command router
- **Day 4**: Backward compatibility
- **Day 5**: Documentation

### Week 2: Core Tools
- **Day 1-2**: Repository & Filesystem
- **Day 3-4**: Codebase & Scaffolder
- **Day 5**: Integration testing

### Week 3: Extended Tools
- **Day 1**: CCT tool
- **Day 2**: AI tool
- **Day 3**: Knowledge tool
- **Day 4-5**: Server/Cloud/Remote tools

### Week 4: Validation
- **Day 1-2**: Unit tests
- **Day 3**: Integration tests
- **Day 4**: Edge case testing
- **Day 5**: Documentation & release notes

---

## 8. Post-Implementation Evaluation

### 8.1 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CLI Coverage | 100% | All 84 commands converted |
| MCP Alignment | 100% | All commands use action pattern |
| Backward Compatibility | 100% | Legacy commands work |
| Test Coverage | >90% | Unit + integration tests |
| Documentation | 100% | All commands documented |

### 8.2 Monitoring

| Aspect | Tool | Frequency |
|--------|------|-----------|
| Command usage | Logs | Daily |
| Error rates | Metrics | Real-time |
| Performance | Benchmarks | Weekly |
| User feedback | Survey | Monthly |

### 8.3 Rollback Plan

If issues found:
1. Set `CLI_MCP_COMPAT_MODE=legacy` to use old parser
2. Revert to previous version via git
3. Notify users via changelog

---

## 9. Files to Modify

| File | Changes |
|------|---------|
| `src/cli/__init__.py` | Complete rewrite for unified parser |
| `src/cli/repository.py` | Remove, merge into main CLI |
| `src/cli/filesystem.py` | Remove, merge into main CLI |
| `src/cli/codebase.py` | Remove, merge into main CLI |
| `src/cli/cct.py` | Convert to MCP action format |
| `src/cli/server.py` | Convert to MCP action format |
| `src/cli/cloud.py` | Convert to MCP action format |
| `src/cli/remote.py` | Convert to MCP action format |
| `src/cli/ai.py` | Convert to MCP action format |
| `docs/usage/cli-guide.md` | Update documentation |

---

## 10. Conclusion

**Implementation Status:**
- ✅ Analysis complete
- ✅ Design documented
- ⏳ Implementation pending

**Key Benefits:**
1. **Unified Interface**: Single consistent pattern across CLI and MCP
2. **Better Discoverability**: `--action` makes available operations clear
3. **Easier Maintenance**: One code path for both interfaces
4. **Full Coverage**: All 84 CLI commands now map to MCP actions

**Next Steps:**
1. Begin Phase 1 implementation
2. Set up CI/CD for testing
3. Create migration guide for users

---

**Prepared by**: AI Implementation Planning  
**Version**: 1.0  
**Status**: Ready for Implementation