# Incremental Indexing Example

Demonstrates VCS-aware incremental indexing with Git and SVN support.

## Git Repository Incremental Update

```python
from src.modules.codeindex.api.tools import code_index

# Incremental re-index after editing a few files
result = code_index(
    action="incremental",
    repo_id="abc-123",
)

print(f"VCS Type: {result['data']['vcs_type']}")
print(f"Files Changed: {result['data']['files_changed']}")
print(f"Duration: {result['data']['duration_s']}s")
print(f"Fallback to Full Sync: {result['data']['fallback_to_full_sync']}")
```

**Output (Git):**
```json
{
  "success": true,
  "message": "Incremental (git): 3 file(s) re-indexed in 0.5s",
  "data": {
    "repo_id": "abc-123",
    "changed_files": ["src/service.py", "src/models.py", "src/api.py"],
    "files_changed": 3,
    "vcs_type": "git",
    "fallback_to_full_sync": false,
    "fallback_reason": null,
    "duration_s": 0.5
  }
}
```

## SVN Repository Incremental Update

```python
# SVN repositories use svn status for changed files
result = code_index(
    action="incremental",
    repo_id="def-456",
)

# SVN automatically falls back to svn diff --summarize if status is empty
print(f"VCS Type: {result['data']['vcs_type']}")
```

**Output (SVN):**
```json
{
  "success": true,
  "message": "Incremental (svn): 5 file(s) re-indexed in 0.8s",
  "data": {
    "repo_id": "def-456",
    "changed_files": ["src/main.c", "include/header.h"],
    "files_changed": 5,
    "vcs_type": "svn",
    "fallback_to_full_sync": false,
    "fallback_reason": null,
    "duration_s": 0.8
  }
}
```

## No VCS Detected (Fallback)

```python
# If no .git or .svn is found, falls back to full sync
result = code_index(
    action="incremental",
    repo_id="ghi-789",
)

print(f"Fallback Reason: {result['data']['fallback_reason']}")
```

**Output (Fallback):**
```json
{
  "success": true,
  "message": "Incremental (fallback full sync, no VCS detected): 0 file(s) in 0.1s",
  "data": {
    "repo_id": "ghi-789",
    "changed_files": [],
    "files_changed": 0,
    "vcs_type": "none",
    "fallback_to_full_sync": true,
    "fallback_reason": "no VCS detected (.git / .svn not found)",
    "duration_s": 0.1
  }
}
```

## Performance Comparison

| Operation | Full Index | Incremental (Git) | Speedup |
|-----------|------------|-------------------|--------|
| 1 file changed | 60s | 0.5s | 120x |
| 5 files changed | 60s | 2.5s | 24x |
| 10 files changed | 60s | 5s | 12x |

## CI/CD Integration

```bash
# In CI pipeline after code changes
codecortex ci incremental --repo-id $REPO_ID

# Check if fallback occurred
if [[ $? -eq 0 ]]; then
    echo "Incremental indexing successful"
else
    echo "Falling back to full index"
    codecortex ci index --repo-id $REPO_ID
fi
```

## Error Handling

```python
try:
    result = code_index(
        action="incremental",
        repo_id="invalid-uuid",
    )
except Exception as e:
    print(f"Error: {e}")
    # Check error code in response
    if result.get("error_code") == "CI_004":
        print("Missing repo_id")
```
