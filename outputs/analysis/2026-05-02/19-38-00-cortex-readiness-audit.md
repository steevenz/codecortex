# CodeCortex Production Readiness Audit

**Date**: 2026-05-02  
**Analysis Type**: Comprehensive Codebase Analysis  
**Target**: CodeCortex Unified Intelligence Engine  
**Reference**: `docs/drafts/final-concept.md`

---

## Executive Summary

**Status**: ❌ **NOT PRODUCTION READY**

CodeCortex implements a promising multi-dimensional intelligence engine but contains **critical bugs**, **schema mismatches**, and **missing production features** that prevent deployment. The codebase demonstrates good architectural intent (DDD, modular monolith) but suffers from implementation gaps that would cause runtime failures.

**Critical Issues Found**: 14  
**High Priority Issues**: 8  
**Medium Priority Issues**: 6  
**Low Priority Issues**: 3

---

## 1. Critical Bugs (Blockers)

### 1.1 Import Mismatch in RepositoryService
**Location**: `src/domain/repository/service.py:9`  
**Severity**: CRITICAL  
**Impact**: Runtime failure on repository sync

**Issue**:
```python
from src.domain.repository.reader import get_file_hash  # ❌ Does not exist
```

`reader.py` defines `calculate_hash()`, not `get_file_hash()`. This will cause an `ImportError` when `RepositoryService.sync_repository()` is called.

**Fix Strategy**:
```python
# Option 1: Rename in reader.py
def get_file_hash(file_path: str) -> str:  # Rename from calculate_hash
    # ... existing logic ...

# Option 2: Update import in service.py
from src.domain.repository.reader import FileReader
# Then use: FileReader.calculate_hash(file_path)
```

**Handoff**: codebase-patch-workflow

---

### 1.2 DatabaseManager Singleton Path Bug
**Location**: `src/core/database.py:27-35`  
**Severity**: CRITICAL  
**Impact**: Database connection corruption across multiple repos

**Issue**:
The singleton pattern ignores the `db_path` parameter after first initialization:
```python
def __init__(self, db_path: Optional[str] = None):
    if self._initialized:
        return  # ❌ Ignores db_path on subsequent calls
```

If you initialize with `db_path="repo1.db"` then later with `db_path="repo2.db"`, both use the first path.

**Fix Strategy**:
```python
def __init__(self, db_path: Optional[str] = None):
    if self._initialized:
        if db_path and Path(db_path) != self.db_path:
            raise ValueError("DatabaseManager already initialized with different path")
        return
```

**Handoff**: codebase-patch-workflow

---

### 1.3 Repository Tools API Mismatch
**Location**: `src/domain/repository/tools.py:25-63`  
**Severity**: CRITICAL  
**Impact**: MCP tools fail at runtime

**Issue**:
Tools call methods that don't exist on `RepositoryService`:
- `service.initialize()` → Service has `sync_repository()`
- `service.get_info()` → Method doesn't exist
- `service.get_structure()` → Service has no such method
- `service.read_file()` → Service has no such method

**Fix Strategy**:
Either implement missing methods in `RepositoryService` or update tools to use existing API.

**Handoff**: codebase-patch-workflow

---

### 1.4 Graphify Tools Broken Imports
**Location**: `src/domain/graphify/tools.py:1-5`  
**Severity**: CRITICAL  
**Impact**: Import failure prevents graphify tools from loading

**Issue**:
```python
from fastmcp import FastMCP  # ❌ Wrong import
from .service import graphify_service  # ❌ Undefined global
from src.core.database import db, Workspace  # ❌ db is not a module, Workspace doesn't exist
```

**Fix Strategy**:
```python
from mcp.server.fastmcp import FastMCP
from .service import GraphifyService
from src.core.database import DatabaseManager
```

**Handoff**: codebase-patch-workflow

---

## 2. Schema Mismatches (final-concept vs Implementation)

### 2.1 Directories Table
**ER Diagram Requirement**:
```sql
directories (
    uuid id PK,
    uuid repository_id FK,
    uuid parent_id FK,
    string relative_path  # ✅ Required
)
```

**Actual Schema** (`core/database.py:53-62`):
```sql
CREATE TABLE directories (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,  # ❌ Should be repository_id
    name TEXT NOT NULL,     # ❌ Extra field not in ER
    path TEXT NOT NULL,     # ❌ Should be relative_path
    parent_id TEXT,
    FOREIGN KEY (parent_id) REFERENCES directories(id)
)
```

**Impact**: Schema drift from design, breaks downstream queries expecting `relative_path`.

**Fix Strategy**: Migrate schema to match ER diagram exactly.

**Handoff**: database-migration-workflow

---

### 2.2 Files Table
**ER Diagram Requirement**:
```sql
files (
    uuid id PK,
    uuid directory_id FK,
    string name,
    enum classification,  # ✅ code|doc|config|binary
    int size_bytes,       # ✅ Required
    string content_hash,  # ✅ Required
    datetime mtime        # ✅ Required
)
```

**Actual Schema**:
```sql
CREATE TABLE files (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL,
    directory_id TEXT,
    name TEXT NOT NULL,
    path TEXT NOT NULL,       # ❌ Extra field
    extension TEXT,          # ❌ Extra field, not in ER
    -- ❌ Missing: classification
    -- ❌ Missing: size_bytes
    -- ❌ Missing: content_hash
    -- ❌ Missing: mtime
)
```

**Impact**: Cannot track file classification, size changes, or modification times for delta analysis.

**Fix Strategy**: Add missing columns, implement classification logic.

**Handoff**: database-migration-workflow

---

### 2.3 Symbols Table Parent Reference
**ER Diagram Requirement**:
```sql
symbols (
    uuid id PK,
    uuid file_id FK,
    uuid parent_id FK,  # ✅ UUID FK to symbols
    string code,       # ✅ Human-readable reference
    ...
)
```

**Actual Schema**:
```sql
CREATE TABLE symbols (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    parent_id TEXT,  # ✅ Correct type
    code TEXT NOT NULL UNIQUE,  # ✅ Present
    ...
)
```

**Code Usage Issue** (`codeindex/service.py:68-69`):
```python
if raw.parent_id and raw.parent_id in code_to_uuid:
    parent_uuid = code_to_uuid[raw.parent_id]  # ❌ parent_id is a code_ref string, not UUID
```

The code stores `code_ref` strings in `parent_id` but the schema expects UUID FKs.

**Impact**: Symbol hierarchy breaks, parent relationships lost.

**Fix Strategy**: Store actual UUIDs in `parent_id`, maintain `code` as separate human-readable field.

**Handoff**: codebase-patch-workflow

---

### 2.4 Manifest Entries Table
**ER Diagram Requirement**:
```sql
manifest_entries (
    uuid id PK,
    uuid repository_id FK,
    string file_path,      # ✅ Required
    string last_hash,      # ✅ Required
    datetime last_processed_at
)
```

**Actual Schema**:
```sql
CREATE TABLE manifest_entries (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    file_path TEXT NOT NULL,  # ✅ Matches
    last_hash TEXT NOT NULL,  # ✅ Matches
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP  # ❌ Should be last_processed_at
)
```

**Impact**: Minor naming inconsistency, but breaks queries expecting `last_processed_at`.

**Fix Strategy**: Rename column to match ER diagram.

**Handoff**: database-migration-workflow

---

### 2.5 Insights Table Metadata Field
**ER Diagram Requirement**:
```sql
insights (
    uuid id PK,
    uuid repository_id FK,
    string target_code FK,
    string category,
    string insight_type,
    json metadata  # ✅ Required
)
```

**Actual Schema**:
```sql
CREATE TABLE insights (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    target_id TEXT,  # ❌ Should be target_code
    category TEXT NOT NULL,
    insight_type TEXT NOT NULL,
    evidence JSON,  # ❌ Should be metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**Impact**: API contract mismatch, downstream consumers expect `metadata`.

**Fix Strategy**: Rename `target_id` → `target_code`, `evidence` → `metadata`.

**Handoff**: database-migration-workflow

---

## 3. Architecture Violations

### 3.1 No Dependency Injection / IoC
**Location**: Multiple service files  
**Severity**: HIGH  
**Impact**: Tight coupling, difficult to test, violates Aegis standards

**Issue**:
All services instantiate their own dependencies:
```python
class CortexOrchestrator:
    def __init__(self, db_path: Optional[str] = None):
        self.db = DatabaseManager(db_path)  # ❌ New instance, not injected
        self.repo_service = RepositoryService(self.db)  # ❌ Direct instantiation
```

**Aegis Standard Requires**:
- Constructor Injection only
- DI Container for dependency management
- No `new Class()` in domain logic

**Fix Strategy**:
Implement DI container or factory pattern:
```python
class ServiceFactory:
    @staticmethod
    def create_orchestrator(db_path: str) -> CortexOrchestrator:
        db = DatabaseManager(db_path)
        repo_service = RepositoryService(db)
        index_service = CodeIndexService(db)
        graph_service = CodeGraphService(db)
        graphify_service = GraphifyService(db)
        return CortexOrchestrator(
            repo_service, index_service, graph_service, graphify_service
        )
```

**Handoff**: architecture-refactor-workflow

---

### 3.2 Missing DTOs for Layer Crossing
**Location**: All service methods  
**Severity**: HIGH  
**Impact**: Raw data leakage, breaks encapsulation

**Issue**:
Services return raw database rows or dicts instead of DTOs:
```python
# repository/service.py:42
cursor.execute("SELECT id, name, path FROM repositories WHERE id = ?", (repo_id,))
return cursor.fetchone()  # ❌ Returns raw sqlite3.Row
```

**Aegis Standard Requires**:
- DTOs for all layer crossings
- Never pass ORM models to UI/external layers

**Fix Strategy**:
Create DTOs and map results:
```python
@dataclass
class RepositoryDTO:
    id: str
    name: str
    path: str
    last_indexed_at: datetime

def get_repository(self, repo_id: str) -> RepositoryDTO:
    cursor.execute(...)
    row = cursor.fetchone()
    return RepositoryDTO(**dict(row))
```

**Handoff**: architecture-refactor-workflow

---

### 3.3 Incomplete Edge Type Implementation
**Location**: `src/domain/codegraph/service.py:80-81`  
**Severity**: MEDIUM  
**Impact**: Missing relationship types

**Issue**:
Only CALLS edges are implemented:
```python
INSERT INTO edges (..., relation_type, ...)
VALUES (..., "CALLS", ...)  # ❌ Only CALLS, no INHERITS/IMPORTS/USES
```

**Final Concept Requires**:
- CALLS
- INHERITS
- IMPORTS
- USES
- DEFINES

**Fix Strategy**:
Implement edge detection strategies for each type.

**Handoff**: feature-implementation-workflow

---

### 3.4 Office Worker is Stub
**Location**: `src/domain/graphify/office_worker.py:14-23`  
**Severity**: MEDIUM  
**Impact**: No Office document conversion

**Issue**:
```python
def convert(self, file_path: Path) -> str:
    # ❌ Returns placeholder, no actual conversion
    return f"# Sidecar for {file_path.name}\n\n[Automatic conversion pending...]"
```

**Final Concept Requires**:
- Pandoc or python-docx integration
- Automated Markdown sidecar generation

**Fix Strategy**:
Implement actual conversion using `pandoc` or `python-docx`.

**Handoff**: feature-implementation-workflow

---

## 4. Missing Production Features

### 4.1 No Test Suite
**Location**: Entire project  
**Severity**: CRITICAL  
**Impact**: Zero test coverage, no regression protection

**Issue**:
No test files found in codebase. No `tests/` directory.

**Production Requires**:
- Unit tests for all services
- Integration tests for pipeline
- E2E tests for MCP tools
- Minimum 80% coverage

**Fix Strategy**:
Create `tests/` directory with pytest structure:
```
tests/
├── unit/
│   ├── test_database.py
│   ├── test_repository_service.py
│   ├── test_codeindex_service.py
│   ├── test_codegraph_service.py
│   └── test_graphify_service.py
├── integration/
│   └── test_pipeline.py
└── e2e/
    └── test_mcp_tools.py
```

**Handoff**: test-implementation-workflow

---

### 4.2 Missing Tree-Sitter Dependencies
**Location**: `pyproject.toml:7-11`  
**Severity**: CRITICAL  
**Impact**: Runtime failure when parsing Python/TypeScript

**Issue**:
```toml
dependencies = [
    "httpx>=0.28.1",
    "mcp[cli]>=1.2.1",
    "pathspec>=0.12.1",
    # ❌ Missing: tree-sitter, tree-sitter-python, tree-sitter-typescript
]
```

**Fix Strategy**:
```toml
dependencies = [
    "httpx>=0.28.1",
    "mcp[cli]>=1.2.1",
    "pathspec>=0.12.1",
    "tree-sitter>=0.21.0",
    "tree-sitter-python>=0.21.0",
    "tree-sitter-typescript>=0.21.0",
]
```

**Handoff**: dependency-update-workflow

---

### 4.3 Empty Tools Files
**Location**: 
- `src/domain/codeindex/tools.py` (empty)
- `src/domain/codegraph/tools.py` (empty)

**Severity**: MEDIUM  
**Impact**: No MCP tools for codeindex/codegraph domains

**Issue**:
No tools registered for these domains, preventing users from querying symbols or relationships directly.

**Fix Strategy**:
Implement tools following pattern from `repository/tools.py`.

**Handoff**: feature-implementation-workflow

---

### 4.4 No Error Handling in MCP Tools
**Location**: `src/main.py:86-97`  
**Severity**: MEDIUM  
**Impact**: Unhandled exceptions crash MCP server

**Issue**:
```python
@mcp.tool()
def analyze_codebase(path: str) -> Dict[str, Any]:
    orchestrator = CortexOrchestrator()
    try:
        result = orchestrator.analyze(path)
        return mcp_response("success", result)
    except Exception as e:
        return mcp_response("error", error=str(e))  # ❌ Generic error, no logging
```

**Production Requires**:
- Structured error logging
- Error classification (transient vs permanent)
- Retry logic for transient errors
- Circuit breaker pattern

**Fix Strategy**:
Implement error handling middleware.

**Handoff**: error-handling-workflow

---

### 4.5 No Configuration Management
**Location**: Entire project  
**Severity**: MEDIUM  
**Impact**: Hardcoded values, no environment-specific configs

**Issue**:
- No config loading from `.env`
- No config validation
- No config schema

**Fix Strategy**:
Implement config using `pydantic-settings`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_path: str = "codecortex.db"
    log_level: str = "INFO"
    max_file_size: int = 10 * 1024 * 1024
    
    class Config:
        env_file = ".env"
```

**Handoff**: config-implementation-workflow

---

### 4.6 Missing `__init__.py` in Core Package
**Location**: `src/core/`  
**Severity**: LOW  
**Impact**: Package import issues

**Issue**:
No `__init__.py` in `src/core/`, may cause import errors.

**Fix Strategy**:
Create empty `src/core/__init__.py`.

**Handoff**: codebase-patch-workflow

---

## 5. Documentation Mismatches

### 5.1 README References Wrong Project
**Location**: `README.md:1-3`  
**Severity**: LOW  
**Impact**: User confusion

**Issue**:
```markdown
# Code Analysis MCP Server  # ❌ Should be "CodeCortex Unified Intelligence Engine"
```

**Fix Strategy**:
Update README to reflect actual project name and capabilities.

**Handoff**: documentation-update-workflow

---

### 5.2 Setup Instructions Reference Non-Existent File
**Location**: `README.md:54-56`  
**Severity**: LOW  
**Impact**: Users cannot follow setup

**Issue**:
```markdown
"run",
"src/code_analysis.py"  # ❌ File doesn't exist, should be "src/main.py"
```

**Fix Strategy**:
Update path to `src/main.py`.

**Handoff**: documentation-update-workflow

---

## 6. Security Concerns

### 6.1 Superficial Secret Detection
**Location**: `src/domain/graphify/service.py:78-86`  
**Severity**: MEDIUM  
**Impact**: False sense of security

**Issue**:
Only checks symbol names for patterns:
```python
patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
cursor.execute("""
    SELECT name, path, start_line
    FROM symbols s
    WHERE s.name LIKE ? OR s.code LIKE ?
""", (repo_id, f"%{p}%", f"%{p}%"))  # ❌ Doesn't check file content
```

**Production Requires**:
- Scan actual file content
- Use regex patterns for common secret formats
- Exclude .env files from indexing
- Implement secret masking before storage

**Fix Strategy**:
Implement content-based secret scanning using `git-secrets` patterns.

**Handoff**: security-hardening-workflow

---

## 7. Performance Issues

### 7.1 N+1 Query Pattern in CodeGraph
**Location**: `src/domain/codegraph/service.py:56-82`  
**Severity**: MEDIUM  
**Impact**: Slow relationship mapping on large codebases

**Issue**:
```python
for f in files:
    file_path = repo_root / f['path']
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
        edge_count += self._map_file_relationships(...)  # ❌ Opens each file sequentially
```

**Fix Strategy**:
Use parallel processing with `concurrent.futures.ThreadPoolExecutor`.

**Handoff**: performance-optimization-workflow

---

## 8. Recommendations Summary

### Immediate Actions (Before Production)
1. ✅ Fix import mismatch (`get_file_hash` → `calculate_hash`)
2. ✅ Fix DatabaseManager singleton bug
3. ✅ Align schema with ER diagram
4. ✅ Add missing dependencies (tree-sitter)
5. ✅ Fix repository tools API mismatch
6. ✅ Fix graphify tools imports

### Short-Term (Sprint 1)
1. ✅ Implement test suite (minimum 80% coverage)
2. ✅ Add error handling middleware
3. ✅ Implement configuration management
4. ✅ Create DTOs for layer crossings
5. ✅ Implement missing edge types (INHERITS, IMPORTS, USES)

### Medium-Term (Sprint 2)
1. ✅ Implement DI container
2. ✅ Add Office document conversion
3. ✅ Implement content-based secret scanning
4. ✅ Optimize CodeGraph with parallel processing
5. ✅ Implement incremental delta analysis

### Long-Term (Sprint 3+)
1. ✅ Add MCP tools for codeindex/codegraph
2. ✅ Implement correlation_id generation
3. ✅ Add circuit breaker patterns
4. ✅ Implement actual Unified Context Envelope generation
5. ✅ Add performance monitoring

---

## 9. Handoff Targets

| Issue | Handoff Workflow | Priority |
|-------|------------------|----------|
| Import mismatch | codebase-patch-workflow | CRITICAL |
| DatabaseManager bug | codebase-patch-workflow | CRITICAL |
| Schema alignment | database-migration-workflow | CRITICAL |
| Missing dependencies | dependency-update-workflow | CRITICAL |
| Repository tools API | codebase-patch-workflow | CRITICAL |
| Graphify tools imports | codebase-patch-workflow | CRITICAL |
| Test suite | test-implementation-workflow | HIGH |
| DTOs | architecture-refactor-workflow | HIGH |
| DI container | architecture-refactor-workflow | HIGH |
| Missing edge types | feature-implementation-workflow | MEDIUM |
| Office conversion | feature-implementation-workflow | MEDIUM |
| Error handling | error-handling-workflow | MEDIUM |
| Config management | config-implementation-workflow | MEDIUM |
| Secret scanning | security-hardening-workflow | MEDIUM |
| Performance optimization | performance-optimization-workflow | MEDIUM |
| Documentation | documentation-update-workflow | LOW |

---

## 10. Conclusion

CodeCortex demonstrates solid architectural intent with its DDD-based modular monolith approach. However, **critical bugs** (import mismatches, singleton issues) and **schema drift** from the final concept prevent production deployment. 

**Estimated Fix Effort**: 3-4 sprints (6-8 weeks) with dedicated engineering team.

**Recommended Next Step**: Address CRITICAL bugs first, then schema alignment, before adding missing features.

**Production Readiness Score**: 2/10 ❌

---

*Generated by Codebase Analysis Workflow v3.1.0*  
*Compliance: Aegis-CrossStack-v1.0*  
*Standard: Aegis Codework v3.1.0*
