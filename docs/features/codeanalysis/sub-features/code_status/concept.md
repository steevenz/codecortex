# Code Status Tool

**Tool:** `code_status`  
**Category:** Project Health  
**Domain:** CodeAnalysis  
**Version:** 2.0.0  
**AI Coder Impact: 10/10 ⭐

---

## Overview

The `code_status` tool provides comprehensive project health metrics and AI readiness scoring. It aggregates code metrics, VCS status, symbol statistics, and graph statistics to give a complete picture of project health.

## Capabilities

### Metrics Collection

- **File Metrics** — Files, directories, total lines, code lines, comment lines, blank lines, comment ratio
- **Language Breakdown** — Lines of code per programming language
- **Symbol Statistics** — Count of symbols by type (class, function, variable, etc.)
- **Graph Statistics** — Nodes, edges, density, components in the knowledge graph
- **VCS Information** — Branch, commit, last commit date, uncommitted changes, untracked files

### AI Readiness Scoring

The tool calculates an AI readiness score based on:
- Documentation coverage
- Symbol density
- Code quality metrics
- VCS cleanliness

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | File or directory path to analyze |
| `repo_id` | string | No | - | Repository UUID for scope |
| `include_metrics` | bool | No | true | Include file and code metrics |
| `include_vcs` | bool | No | true | Include VCS information |
| `include_symbols` | bool | No | true | Include symbol statistics |
| `language` | string | No | - | Filter by programming language |

## Output

### Result Structure

```json
{
  "target": "/path/to/code",
  "repo_id": "repo-uuid",
  "summary": {
    "files": 150,
    "directories": 25,
    "total_lines": 12500,
    "code_lines": 8750,
    "comment_lines": 2500,
    "blank_lines": 1250,
    "comment_ratio": 0.2
  },
  "languages": {
    "python": 8500,
    "javascript": 3000,
    "typescript": 1000
  },
  "symbols": {
    "class": 25,
    "function": 120,
    "variable": 85,
    "constant": 15
  },
  "graph_stats": {
    "nodes": 245,
    "edges": 512,
    "density": 0.017,
    "components": 3
  },
  "vcs": {
    "type": "git",
    "branch": "main",
    "commit": "abc123",
    "last_commit_date": "2024-05-28T10:30:00Z",
    "uncommitted_changes": 3,
    "untracked_files": 5
  }
}
```

### Metrics Details

#### File Metrics

- **files** — Total number of files
- **directories** — Total number of directories
- **total_lines** — Total lines of code
- **code_lines** — Lines containing code (non-comment, non-blank)
- **comment_lines** — Lines containing comments
- **blank_lines** — Empty lines
- **comment_ratio** — comment_lines / total_lines

#### Language Breakdown

Key-value pairs where keys are programming languages and values are line counts.

#### Symbol Statistics

- **class** — Number of classes
- **function** — Number of functions
- **variable** — Number of variables
- **constant** — Number of constants
- Other symbol types as detected

#### Graph Statistics

- **nodes** — Total nodes in knowledge graph
- **edges** — Total edges (relationships)
- **density** — Graph density (edges / possible edges)
- **components** — Number of connected components

#### VCS Information

- **type** — VCS type (git, svn, none)
- **branch** — Current branch name
- **commit** — Current commit hash
- **last_commit_date** — Timestamp of last commit
- **uncommitted_changes** — Number of uncommitted files
- **untracked_files** — Number of untracked files

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| CA_030 | high | Path is required for status |
| CA_031 | high | Path does not exist |
| CA_500 | critical | Internal error |

## Examples

### Basic Status

```python
# Get complete project status
result = code_status(path="src/")
```

### Metrics Only

```python
# Only file and code metrics
result = code_status(
    path="src/",
    include_metrics=True,
    include_vcs=False,
    include_symbols=False,
)
```

### VCS Only

```python
# Only VCS information
result = code_status(
    path="src/",
    include_metrics=False,
    include_vcs=True,
    include_symbols=False,
)
```

### Language Filter

```python
# Status for specific language
result = code_status(
    path="src/",
    language="python",
)
```

## Performance

- **Database Queries** — Optimized with indexes
- **Caching** — Metrics cached for 5 minutes
- **VCS Integration** — Efficient git operations
- **Graph Queries** — Optimized for large graphs

## Dependencies

- **Database** — Symbol and metadata storage
- **VCS** — Git integration for version control
- **Filesystem Service** — File discovery and analysis
- **Graph Database** — Knowledge graph queries

## AI Readiness Score

The AI readiness score is calculated based on:

1. **Documentation Coverage** — DocBlock presence and completeness
2. **Symbol Density** — Symbols per line of code
3. **Code Quality** — Comment ratio, blank line ratio
4. **VCS Cleanliness** - Uncommitted changes, untracked files

Score ranges from 0-100, with higher scores indicating better AI readiness.

## See Also

- [Analyze Tool](../sub-features/code_analyze/concept.md)
- [Search Tool](../sub-features/code_search/concept.md)
- [Audit Tool](../sub-features/code_audit/concept.md)
