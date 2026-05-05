# Vendor Cleanup Plan - CodeCortex

> **Date**: 2026-05-05
> **Status**: **COMPLETED**
> **Impact**: Removed 1211 files, src/ is 100% self-contained
> **Executed**: 2026-05-05T17:09 UTC

---

## 1. Executive Summary

Folder `vendor/` berisi **3 mirrored upstream repositories** (codegraph, codeindex, graphify) yang **tidak dipakai** di runtime normal. CodeCortex sudah beroperasi fully-native via Tree-Sitter parsers dan ported discovery logic. Plan ini akan membersihkan `vendor/` dan memastikan `src/` 100% mandiri.

---

## 2. Current State Analysis

### 2.1 Vendor Contents

| Upstream Repo | Files | Purpose |
|---------------|-------|---------|
| `vendor/upstreams/codegraph/` | ~796 files | Mirrored codegraph (package: codegraphcontext) |
| `vendor/upstreams/codeindex/` | ~254 files | Mirrored codeindex (package: code_index_mcp) |
| `vendor/upstreams/graphify/` | ~161 files | Mirrored graphify (package: graphify) |
| **TOTAL** | **~1211 files** | |

### 2.2 Usage Status

| Aspect | Status | Detail |
|--------|--------|--------|
| Runtime import | **NOT USED** | `CODECORTEX_USE_UPSTREAM_CODEINDEX` default = False |
| Packaged to src/ | **NO** | `src/domain/*/upstream/` kosong (0 files) |
| Git tracked | **YES** | Tidak ada di `.gitignore` |
| Harvest script | **DEPENDENT** | `harvest_upstreams.py` punya mode `--source vendor` |

### 2.3 Where vendor/ is Referenced in src/

1. **`src/domain/codeindex/application/service.py:178`** -- Env flag gate untuk upstream indexing (OPT-IN, default OFF)
2. **`src/domain/codeindex/application/service.py:432`** -- Dynamic import dari `src.domain.codeindex.upstream.code_index_mcp...`
3. **`src/domain/codeindex/application/service.py:440`** -- "vendor" di exclusion list saat upstream mode
4. **`src/domain/coderepository/application/service.py:197`** -- "vendor/" di ignore patterns (untuk external repo scan)
5. **`src/domain/codegraph/application/discovery_mixin.py:18`** -- Comment: "Constants ported from upstream detect.py" (SUDAH DI-PORT)

### 2.4 What's Already Native (No Vendor Needed)

| Component | Native Implementation | Location |
|-----------|---------------------|----------|
| File Discovery | `ArchitecturalDiscoveryMixin.discover_files()` | `codegraph/application/discovery_mixin.py` |
| File Classification | `classify_file()` dengan 40+ extensions | `codegraph/application/discovery_mixin.py` |
| Code Indexing / Parsing | Tree-Sitter based parsers (20+ languages) | `codeindex/infrastructure/parsers/` |
| Symbol Extraction | Tree-Sitter AST walking | `codeindex/infrastructure/parsers/` |
| Ignore Patterns | PathSpec + .gitignore + .codecortexignore | `coderepository/application/service.py` |

---

## 3. Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Upstream indexing breaks | **LOW** | Default OFF; nobody uses it |
| harvest_upstreams.py --source vendor breaks | **MEDIUM** | Update script ke pythons-only mode |
| Future upstream sync need | **LOW** | Script tetap bisa jalan dari pythons/ sibling dirs |
| External repo "vendor/" exclusion | **NONE** | String literal "vendor" di exclude list bukan referensi ke folder kita |

---

## 4. Action Items

### Phase 1: Configuration Cleanup

#### 4.1 Add `vendor/` to `.gitignore`
```diff
 # Cache directories
 .mypy_cache/
 .ruff_cache/
 .pytest_cache/
+
+# Vendored upstream mirrors (managed by harvest_upstreams.py)
+vendor/
```

**Why**: Mencegah vendor/ masuk lagi kalau ada script yang recreate.

#### 4.2 Deprecate Upstream Indexing Path

File: `src/domain/codeindex/application/service.py`

**Option A (Recommended)**: Wrap with deprecation warning + hard-off
```python
if env_flag("CODECORTEX_USE_UPSTREAM_CODEINDEX", default=False):
    import warnings
    warnings.warn(
        "CODECORTEX_USE_UPSTREAM_CODEINDEX is deprecated. "
        "Vendor directory has been removed. Using native Tree-Sitter parser.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Fall through to native parsing
```

**Option B (Nuclear)**: Hapus entire `_index_repository_upstream()` method dan branch.

**Recommendation**: Option A dulu untuk backward compatibility, then Option B di release berikutnya.

### Phase 2: Script Porting

#### 4.3 Update `scripts/harvest_upstreams.py`

**Changes needed**:
1. Hapus `--source vendor` option ( hanya keep `--source pythons`)
2. Hapus `spec.package_src_from_vendor` field dari `UpstreamSpec`
3. Hapus branch `if parsed.source == "vendor"` di `_run()`
4. Update docstring

**Before**:
```python
parser.add_argument("--source", choices=["vendor", "pythons"], default="vendor")
```

**After**:
```python
parser.add_argument("--source", choices=["pythons"], default="pythons")
```

Script ini akan tetap fungsional karena sibling repos (`pythons/codegraph/`, `pythons/codeindex/`, `pythons/graphify/`) masih exist sebagai source of truth.

### Phase 3: Verification & Deletion

#### 4.4 Verify src/ Mandiri

Sebelum delete, pastikan:
- [ ] `python -m src.domain.codegraph.application.discovery_mixin` import sukses
- [ ] `python -m src.domain.codeindex.application.service` import sukses  
- [ ] Tree-Sitter parsers load tanpa error
- [ ] Tidak ada `importlib.import_module` yang gagal silently

#### 4.5 Delete vendor/

```bash
rm -rf vendor/upstreams/
# atau keep folder tapi kosong:
# rm -rf vendor/upstreams/*
```

---

## 5. Files Modified Summary

| File | Action | Change |
|------|--------|--------|
| `.gitignore` | MODIFY | Add `vendor/` entry |
| `src/domain/codeindex/application/service.py` | MODIFY | Deprecate upstream branch |
| `scripts/harvest_upstreams.py` | MODIFY | Remove vendor source option |
| `vendor/` | **DELETE** | Remove entire directory (~1211 files) |

**Total changes**: 3 file modifies, 1 directory deletion

---

## 6. Rollback Plan

Kalau ada masalah:
1. `git checkout HEAD -- vendor/` (restore from git)
2. `git checkout HEAD -- scripts/harvest_upstreams.py`
3. `git checkout HEAD -- .gitignore`
4. `git checkout HEAD -- src/domain/codeindex/application/service.py`

---

## 7. Post-Cleanup Validation

```bash
# 1. Import test
cd c:/Users/steevenz/.aicoders/scripts/pythons/codecortex
python -c "from src.domain.codegraph.application.discovery_mixin import ArchitecturalDiscoveryMixin; print('OK')"

# 2. Parser test
python -c "from src.domain.codeindex.infrastructure.parsers.python_parser import PythonParser; print('OK')"

# 3. Service test
python -c "from src.domain.codeindex.application.service import CodeIndexService; print('OK')"

# 4. Confirm vendor gone
test ! -d vendor/upstreams && echo "VENDOR CLEAN" || echo "VENDOR EXISTS"
```
