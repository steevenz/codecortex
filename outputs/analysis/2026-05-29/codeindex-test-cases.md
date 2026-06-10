# CodeIndex Test Cases

**Date:** 2026-05-29
**Domain:** CodeIndex
**Scope:** MCP Tool `code_index` (5 actions)
**Total Test Scenarios:** 25

---

## Test Case Matrix

### Action: `status` (5 scenarios)

#### Scenario 1.1: Basic status check with valid repo_id
```json
{
  "scenario_id": "1.1",
  "description": "Basic status check with valid repository UUID",
  "tool": "code_index",
  "parameters": {
    "action": "status",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "valid-repo-uuid",
      "symbol_count": 0,
      "file_count": 0,
      "sync_at": null
    }
  }
}
```

#### Scenario 1.2: Status check with indexed repository
```json
{
  "scenario_id": "1.2",
  "description": "Status check with repository that has been indexed",
  "tool": "code_index",
  "parameters": {
    "action": "status",
    "repo_id": "indexed-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "symbol_count": 142,
      "file_count": 23
    }
  }
}
```

#### Scenario 1.3: Status check with missing repo_id
```json
{
  "scenario_id": "1.3",
  "description": "Status check without required repo_id parameter",
  "tool": "code_index",
  "parameters": {
    "action": "status"
  },
  "expected_status": 400,
  "expected_error_code": "CI_002",
  "expected_message": "repo_id required for status"
}
```

#### Scenario 1.4: Status check with non-existent repo_id
```json
{
  "scenario_id": "1.4",
  "description": "Status check with non-existent repository UUID",
  "tool": "code_index",
  "parameters": {
    "action": "status",
    "repo_id": "non-existent-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "symbol_count": 0,
      "file_count": 0,
      "sync_at": null
    }
  }
}
```

#### Scenario 1.5: Status check with invalid action
```json
{
  "scenario_id": "1.5",
  "description": "Status check with invalid action parameter",
  "tool": "code_index",
  "parameters": {
    "action": "invalid_action",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 400,
  "expected_error_code": "CI_001",
  "expected_message": "action must be one of"
}
```

---

### Action: `index` (5 scenarios)

#### Scenario 2.1: Full index with repo_id
```json
{
  "scenario_id": "2.1",
  "description": "Full re-index with existing repository UUID",
  "tool": "code_index",
  "parameters": {
    "action": "index",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "valid-repo-uuid",
      "duration_s": 12.5
    }
  }
}
```

#### Scenario 2.2: Full index with path (auto-sync)
```json
{
  "scenario_id": "2.2",
  "description": "Full re-index with repository path (triggers auto-sync)",
  "tool": "code_index",
  "parameters": {
    "action": "index",
    "path": "/path/to/repository"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "auto-generated-uuid",
      "duration_s": 15.2
    }
  }
}
```

#### Scenario 2.3: Index with missing repo_id and path
```json
{
  "scenario_id": "2.3",
  "description": "Index without repo_id or path parameters",
  "tool": "code_index",
  "parameters": {
    "action": "index"
  },
  "expected_status": 400,
  "expected_error_code": "CI_003",
  "expected_message": "Provide repo_id or path"
}
```

#### Scenario 2.4: Index with small repository (sequential path)
```json
{
  "scenario_id": "2.4",
  "description": "Index small repository (<15 files, <512KB) uses sequential async",
  "tool": "code_index",
  "parameters": {
    "action": "index",
    "repo_id": "small-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "small-repo-uuid",
      "duration_s": 2.1
    }
  }
}
```

#### Scenario 2.5: Index with large repository (WorkerPool path)
```json
{
  "scenario_id": "2.5",
  "description": "Index large repository (>=15 files or >=512KB) uses WorkerPool",
  "tool": "code_index",
  "parameters": {
    "action": "index",
    "repo_id": "large-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "large-repo-uuid",
      "duration_s": 25.3
    }
  }
}
```

---

### Action: `incremental` (5 scenarios)

#### Scenario 3.1: Incremental index with changes
```json
{
  "scenario_id": "3.1",
  "description": "Incremental index with git changes detected",
  "tool": "code_index",
  "parameters": {
    "action": "incremental",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "valid-repo-uuid",
      "changed_files": ["file1.py", "file2.py"],
      "duration_s": 3.2
    }
  }
}
```

#### Scenario 3.2: Incremental index with no changes
```json
{
  "scenario_id": "3.2",
  "description": "Incremental index with no git changes (crash guard)",
  "tool": "code_index",
  "parameters": {
    "action": "incremental",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "valid-repo-uuid",
      "changed_files": [],
      "duration_s": 0.5
    }
  }
}
```

#### Scenario 3.3: Incremental index with missing repo_id
```json
{
  "scenario_id": "3.3",
  "description": "Incremental index without required repo_id",
  "tool": "code_index",
  "parameters": {
    "action": "incremental"
  },
  "expected_status": 400,
  "expected_error_code": "CI_004",
  "expected_message": "repo_id required"
}
```

#### Scenario 3.4: Incremental index with no git history
```json
{
  "scenario_id": "3.4",
  "description": "Incremental index on repository without git history",
  "tool": "code_index",
  "parameters": {
    "action": "incremental",
    "repo_id": "no-git-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "no-git-repo-uuid",
      "changed_files": [],
      "duration_s": 0.3
    }
  }
}
```

#### Scenario 3.5: Incremental index with single file change
```json
{
  "scenario_id": "3.5",
  "description": "Incremental index with single file changed",
  "tool": "code_index",
  "parameters": {
    "action": "incremental",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "valid-repo-uuid",
      "changed_files": ["src/service.py"],
      "duration_s": 1.8
    }
  }
}
```

---

### Action: `files` (5 scenarios)

#### Scenario 4.1: Index specific files
```json
{
  "scenario_id": "4.1",
  "description": "Index specific files by relative path",
  "tool": "code_index",
  "parameters": {
    "action": "files",
    "repo_id": "valid-repo-uuid",
    "files": ["src/service.py", "src/models.py"]
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "files_requested": 2,
      "files_indexed": 2,
      "errors": [],
      "duration_s": 1.5
    }
  }
}
```

#### Scenario 4.2: Index single file
```json
{
  "scenario_id": "4.2",
  "description": "Index single file",
  "tool": "code_index",
  "parameters": {
    "action": "files",
    "repo_id": "valid-repo-uuid",
    "files": ["src/service.py"]
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "files_requested": 1,
      "files_indexed": 1,
      "errors": [],
      "duration_s": 0.8
    }
  }
}
```

#### Scenario 4.3: Index files with missing repo_id
```json
{
  "scenario_id": "4.3",
  "description": "Index files without required repo_id",
  "tool": "code_index",
  "parameters": {
    "action": "files",
    "files": ["src/service.py"]
  },
  "expected_status": 400,
  "expected_error_code": "CI_005",
  "expected_message": "repo_id and files required"
}
```

#### Scenario 4.4: Index files with missing files parameter
```json
{
  "scenario_id": "4.4",
  "description": "Index files without required files parameter",
  "tool": "code_index",
  "parameters": {
    "action": "files",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 400,
  "expected_error_code": "CI_005",
  "expected_message": "repo_id and files required"
}
```

#### Scenario 4.5: Index non-existent files
```json
{
  "scenario_id": "4.5",
  "description": "Index files that don't exist in repository",
  "tool": "code_index",
  "parameters": {
    "action": "files",
    "repo_id": "valid-repo-uuid",
    "files": ["nonexistent/file.py"]
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "files_requested": 1,
      "files_indexed": 0,
      "errors": ["File not found: nonexistent/file.py"],
      "duration_s": 0.2
    }
  }
}
```

---

### Action: `pre_scan` (5 scenarios)

#### Scenario 5.1: Pre-scan with repo_id
```json
{
  "scenario_id": "5.1",
  "description": "Pre-scan Python imports with repository UUID",
  "tool": "code_index",
  "parameters": {
    "action": "pre_scan",
    "repo_id": "valid-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "valid-repo-uuid",
      "modules": 15,
      "symbols": 142,
      "duration_s": 2.1
    }
  }
}
```

#### Scenario 5.2: Pre-scan with path (auto-sync)
```json
{
  "scenario_id": "5.2",
  "description": "Pre-scan with repository path (triggers auto-sync)",
  "tool": "code_index",
  "parameters": {
    "action": "pre_scan",
    "path": "/path/to/repository"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "auto-generated-uuid",
      "modules": 10,
      "symbols": 85,
      "duration_s": 2.5
    }
  }
}
```

#### Scenario 5.3: Pre-scan with missing repo_id and path
```json
{
  "scenario_id": "5.3",
  "description": "Pre-scan without repo_id or path parameters",
  "tool": "code_index",
  "parameters": {
    "action": "pre_scan"
  },
  "expected_status": 400,
  "expected_error_code": "CI_006",
  "expected_message": "Provide repo_id or path"
}
```

#### Scenario 5.4: Pre-scan repository with no Python files
```json
{
  "scenario_id": "5.4",
  "description": "Pre-scan repository with no Python files",
  "tool": "code_index",
  "parameters": {
    "action": "pre_scan",
    "repo_id": "no-python-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "no-python-repo-uuid",
      "modules": 0,
      "symbols": 0,
      "duration_s": 0.5
    }
  }
}
```

#### Scenario 5.5: Pre-scan large Python codebase
```json
{
  "scenario_id": "5.5",
  "description": "Pre-scan large Python codebase with many imports",
  "tool": "code_index",
  "parameters": {
    "action": "pre_scan",
    "repo_id": "large-python-repo-uuid"
  },
  "expected_status": 200,
  "expected_output": {
    "success": true,
    "data": {
      "repo_id": "large-python-repo-uuid",
      "modules": 50,
      "symbols": 500,
      "duration_s": 8.3
    }
  }
}
```

---

## Test Coverage Summary

| Action | Happy Path | Error Scenarios | Edge Cases | Total |
|--------|------------|-----------------|------------|-------|
| status | 2 | 2 | 1 | 5 |
| index | 3 | 1 | 1 | 5 |
| incremental | 2 | 1 | 2 | 5 |
| files | 2 | 2 | 1 | 5 |
| pre_scan | 2 | 1 | 2 | 5 |
| **Total** | **11** | **7** | **7** | **25** |

**Coverage Goals:**
- Minimum: 10 critical scenarios ✅ (25 designed)
- Ideal: All designed scenarios ✅ (25 designed)
- Happy Path: 44% (11/25)
- Error Scenarios: 28% (7/25)
- Edge Cases: 28% (7/25)

---

## Integration Scenarios

### Scenario 6.1: Full pipeline (sync -> index -> graph)
```json
{
  "scenario_id": "6.1",
  "description": "End-to-end pipeline via repo_analyze tool",
  "tool": "repo_analyze",
  "parameters": {
    "path": "/path/to/repository"
  },
  "expected_status": 200,
  "expected_pipeline": [
    "sync_repository",
    "index_repository",
    "build_graph",
    "extract_vcs_info"
  ]
}
```

### Scenario 6.2: Cross-tool workflow (index -> search)
```json
{
  "scenario_id": "6.2",
  "description": "Index then search for symbols",
  "tools": [
    {
      "tool": "code_index",
      "action": "index",
      "repo_id": "valid-repo-uuid"
    },
    {
      "tool": "code_search",
      "query": "function_name"
    }
  ],
  "expected_status": 200,
  "expected_result": "Symbols found after indexing"
}
```

---

## Test Execution Notes

### Prerequisites
1. Test repository must exist in filesystem
2. Database must be initialized
3. Orchestrator must be properly configured
4. CodeIndex service must be injected

### Test Data Requirements
- Small repository: <15 files, <512KB total
- Large repository: >=15 files or >=512KB total
- Python repository: Contains .py/.ipynb files
- Non-Python repository: No Python files
- Repository with git history: For incremental tests
- Repository without git history: For crash guard tests

### Execution Order
1. Execute happy path scenarios first
2. Execute error scenarios
3. Execute edge case scenarios
4. Execute integration scenarios last

### Success Criteria
- All 25 scenarios execute without runtime errors
- All error codes match expected values
- All response formats match documentation
- Timing measurements are reasonable (<60s for index)
