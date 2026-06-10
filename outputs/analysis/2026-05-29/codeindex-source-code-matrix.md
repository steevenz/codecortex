# CodeIndex Source Code Matrix

**Date:** 2026-05-29
**Domain:** CodeIndex
**Scope:** MCP Tools (1 tool with 5 actions)
**Source:** `src/modules/codeindex/api/tools.py`

---

## Tool: `code_index`

**Source File:** `src/modules/codeindex/api/tools.py`
**Function Signature:** `async def code_index(action: str, repo_id: Optional[str] = None, path: Optional[str] = None, files: Optional[List[str]] = None) -> Dict[str, Any]`

**Implemented Parameters:**
| Parameter | Type | Required | Default | Source Line |
|-----------|------|----------|---------|-------------|
| action | str | Yes | - | 22 |
| repo_id | Optional[str] | Conditional | None | 24 |
| path | Optional[str] | Conditional | None | 25 |
| files | Optional[List[str]] | Conditional | None | 26 |

**Valid Actions:** `{"status", "index", "incremental", "files", "pre_scan"}` (line 56)

---

### Action: `status`

**Implementation Lines:** 63-82

**Parameter Validation:**
```python
if not repo_id:
    return api_response(success=False, status_code=400,
        message="repo_id required for status", data=None,
        request_id=req_id, error_code="CI_002")
```

**Database Queries:**
```python
# Symbol count
symbol_count = orchestrator.db.conn.execute(
    "SELECT COUNT(1) FROM symbols WHERE repository_id = ?", (repo_id,)
).fetchone()[0]

# File count
file_count = orchestrator.db.conn.execute(
    "SELECT COUNT(1) FROM files WHERE repository_id = ? AND is_deleted = 0", (repo_id,)
).fetchone()[0]

# Last sync time
row = orchestrator.db.conn.execute(
    "SELECT sync_at FROM repositories WHERE id = ?", (repo_id,)
).fetchone()
```

**Actual Response Format:**
```python
return api_response(success=True, insight="code_index", status_code=200,
    message=f"Status: {symbol_count} symbols, {file_count} files",
    data={"repo_id": repo_id, "symbol_count": symbol_count,
          "file_count": file_count,
          "sync_at": row["sync_at"] if row else None},
    request_id=req_id)
```

**Error Codes Implemented:**
- CI_002: repo_id required for status

**Adapter/Service Used:**
- `orchestrator.db.conn` - Direct database access
- No adapter used (direct SQL queries)

---

### Action: `index`

**Implementation Lines:** 84-95

**Parameter Validation:**
```python
if not repo_id and not path:
    return api_response(success=False, status_code=400,
        message="Provide repo_id or path", data=None,
        request_id=req_id, error_code="CI_003")
```

**Auto-Sync Logic:**
```python
if not repo_id and path:
    repo_id = await orchestrator.repo_service.sync_repository(path)
```

**Service Call:**
```python
await index_service.index_repository(repo_id, request_id=req_id)
```

**Actual Response Format:**
```python
return api_response(success=True, insight="code_index", status_code=200,
    message=f"Indexing completed for {repo_id}",
    data={"repo_id": repo_id, "duration_s": round(time.time() - start, 2)},
    request_id=req_id)
```

**Error Codes Implemented:**
- CI_003: Provide repo_id or path

**Adapter/Service Used:**
- `orchestrator.repo_service.sync_repository(path)` - Repository sync service
- `index_service.index_repository(repo_id, request_id=req_id)` - Index service

---

### Action: `incremental`

**Implementation Lines:** 97-113

**Parameter Validation:**
```python
if not repo_id:
    return api_response(success=False, status_code=400,
        message="repo_id required", data=None,
        request_id=req_id, error_code="CI_004")
```

**Service Call:**
```python
result = await orchestrator.repo_service.sync_repository_incremental(repo_id)
if isinstance(result, tuple) and len(result) == 2:
    repo_id, changed = result
else:
    changed = []
if changed:
    await index_service.index_files(repo_id, changed, request_id=req_id)
```

**Crash Guard Implementation:**
```python
# Lines 103-106: Handle case where result is not a tuple
if isinstance(result, tuple) and len(result) == 2:
    repo_id, changed = result
else:
    changed = []
```

**Actual Response Format:**
```python
return api_response(success=True, insight="code_index", status_code=200,
    message=f"Incremental: {len(changed or [])} files processed",
    data={"repo_id": repo_id, "changed_files": changed or [],
          "duration_s": round(time.time() - start, 2)},
    request_id=req_id)
```

**Error Codes Implemented:**
- CI_004: repo_id required

**Adapter/Service Used:**
- `orchestrator.repo_service.sync_repository_incremental(repo_id)` - Incremental sync service
- `index_service.index_files(repo_id, changed, request_id=req_id)` - Index files service

---

### Action: `files`

**Implementation Lines:** 115-124

**Parameter Validation:**
```python
if not repo_id or not files:
    return api_response(success=False, status_code=400,
        message="repo_id and files required", data=None,
        request_id=req_id, error_code="CI_005")
```

**Service Call:**
```python
result = await index_service.index_files(repo_id, files, request_id=req_id)
```

**Actual Response Format:**
```python
return api_response(success=True, insight="code_index", status_code=200,
    message=f"Indexed {len(files)} file(s)",
    data={**result, "duration_s": round(time.time() - start, 2)},
    request_id=req_id)
```

**Error Codes Implemented:**
- CI_005: repo_id and files required

**Adapter/Service Used:**
- `index_service.index_files(repo_id, files, request_id=req_id)` - Index files service

---

### Action: `pre_scan`

**Implementation Lines:** 126-139

**Parameter Validation:**
```python
if not repo_id and not path:
    return api_response(success=False, status_code=400,
        message="Provide repo_id or path", data=None,
        request_id=req_id, error_code="CI_006")
```

**Auto-Sync Logic:**
```python
if not repo_id and path:
    repo_id = await orchestrator.repo_service.sync_repository(path)
```

**Service Call:**
```python
imports_map = await index_service.pre_scan_repository(repo_id, request_id=req_id)
total = sum(len(v) for v in imports_map.values())
```

**Actual Response Format:**
```python
return api_response(success=True, insight="code_index", status_code=200,
    message=f"Pre-scan: {len(imports_map)} modules, {total} symbols",
    data={"repo_id": repo_id, "modules": len(imports_map), "symbols": total,
          "duration_s": round(time.time() - start, 2)},
    request_id=req_id)
```

**Error Codes Implemented:**
- CI_006: Provide repo_id or path

**Adapter/Service Used:**
- `orchestrator.repo_service.sync_repository(path)` - Repository sync service
- `index_service.pre_scan_repository(repo_id, request_id=req_id)` - Pre-scan service

---

## Global Error Handling

**Implementation Lines:** 141-144

```python
except Exception as e:
    return api_response(success=False, status_code=500,
        message=f"code_index failed: {str(e)}", data=None,
        request_id=req_id, error_code="CI_500")
```

**Error Codes Implemented:**
- CI_500: code_index failed (catch-all for all exceptions)

---

## Implementation Quality Assessment

### Parameter Exposure
- **Status:** ✅ All parameters correctly exposed in function signature
- **Types:** ✅ All parameters have correct type hints
- **Defaults:** ✅ Optional parameters have None defaults
- **Validation:** ✅ All required parameters validated before use

### Adapter Integration
- **Status:** ✅ Correct service usage via orchestrator
- **Services Used:**
  - `orchestrator.db.conn` - Direct database access (status action)
  - `orchestrator.repo_service.sync_repository()` - Repository sync
  - `orchestrator.repo_service.sync_repository_incremental()` - Incremental sync
  - `index_service.index_repository()` - Full index
  - `index_service.index_files()` - File-specific index
  - `index_service.pre_scan_repository()` - Pre-scan imports

### Error Handling
- **Status:** ✅ Comprehensive error handling
- **Validation:** ✅ All required parameters validated
- **Error Codes:** ✅ All documented error codes implemented
- **Catch-All:** ✅ Global exception handler with CI_500

### Security Validations
- **Status:** ⚠️ No explicit path validation in tools.py
- **Note:** Path validation should be handled by underlying services
- **Recommendation:** Verify that `repo_service.sync_repository()` validates paths

### Cross-Platform Compatibility
- **Status:** ✅ Uses asyncio for async operations
- **Path Handling:** ⚠️ Uses `Path` objects in services but string paths in tools
- **Note:** Should verify path normalization in service layer

---

## Source Code Strengths
- Clean function signature with proper type hints
- Comprehensive parameter validation
- Consistent error code usage
- Proper service integration via orchestrator pattern
- Crash guard for incremental action (lines 103-106)
- Auto-sync logic for path-based operations
- Timing measurement for all operations

## Source Code Observations
1. **Direct Database Access:** `status` action uses direct SQL queries instead of service layer
2. **Response Field Mismatch:** Documentation says `last_indexed_at` but code returns `sync_at`
3. **No Path Validation:** Tools layer doesn't validate paths (delegated to services)
4. **Crash Guard:** Good implementation for incremental action edge case

---

## Summary

**Total MCP Tools:** 1
**Total Actions:** 5
**Total CLI Commands:** 0
**Implementation Completeness:** 100%
**Parameter Exposure:** 100%
**Error Handling:** 100%
**Service Integration:** 100%
