# Incremental Scan Example

Demonstrates incremental scanning for CI/CD pipelines with the `code_audit` tool.

## CI/CD Integration

```python
from src.modules.codeanalysis.api.tools import code_audit
import os

# Get last commit date from git
commit_date = os.environ.get("COMMIT_DATE", "2024-01-01T00:00:00Z")

# Incremental scan - only files modified since last commit
result = code_audit(
    target=".",
    since=commit_date,  # Only scan changed files
    severity_threshold="high",
    enable_auto_fix=True,
    dry_run=True,  # Safety: don't modify in CI
)

# Fail build if compliance score < 90
if result['compliance_score'] < 90:
    print(f"Compliance score {result['compliance_score']} < 90, failing build")
    sys.exit(1)

print(f"Scanned {result['scanned_files']} files, compliance score: {result['compliance_score']}")
```

## Performance Improvement

Full scan: 5 minutes  
Incremental scan: 30 seconds  
**10x faster for CI/CD**

## Local Development

```python
# Scan only files modified in last hour
from datetime import datetime, timedelta

one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

result = code_audit(
    target="src/",
    since=one_hour_ago,
)
```

## Error Handling

If timestamp is invalid, falls back to full scan:

```python
result = code_audit(
    target="src/",
    since="invalid-timestamp",  # Falls back to full scan
)
```
