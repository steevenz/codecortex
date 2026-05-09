# Import Resolution Pipeline

**Domain:** CodeIndexing  
**Effort:** High | **Impact:** High | **Priority:** 9

## Current State
CodeCortex's CodeIndex parses AST and extracts local symbols but does NOT resolve imports cross-file. No way to answer: "This file imports from utils/helper.py — what does it use?" This limits:
- Cross-file reference tracking
- Dependency graph accuracy
- Refactoring impact analysis
- Call graph completeness

## Proposed Improvement
Port GitNexus's import resolution system with per-language resolvers:
1. **Import Decomposer**: Per-language logic to parse import statements
   - Python: `from foo.bar import Baz` → `{source: "foo.bar", names: ["Baz"], type: "named"}`
   - TypeScript: `import { Foo } from './foo'` → `{source: "./foo", names: ["Foo"], type: "named"}`
   - Go: `import "fmt"` → `{source: "fmt", type: "default"}`
2. **Suffix Index**: `dict[suffix, set[FilePath]]` for fast resolution
3. **Resolution Context**: Per-file scope resolution with alias maps
4. **Implicit Imports**: Per-language wiring (e.g., Python __init__.py, TypeScript barrel files)

## Architecture
```
resolve_imports(files, parse_results)
  ├── build_suffix_index(files) → suff_index
  ├── for each file:
  │     imports = decompose_imports(file, language)
  │     for each import:
  │         resolved = resolve_single_import(import, file, suff_index, aliases)
  │         store_import_edge(file, resolved)
  ├── wire_implicit_imports(files, language_providers)
  └── return ImportMap

decompose_imports(file, language):
  ├── Python: import_decomposer_python()
  ├── TS/JS: import_decomposer_typescript()
  ├── Go: import_decomposer_go()
  └── ... (10+ languages)
```

## Key Changes in CodeCortex
- **`src/domain/codeindex/infrastructure/`**: New `import_resolvers/` directory  
  - `base.py`: ImportResolver interface  
  - `python.py`: Python import decomposer  
  - `typescript.py`: TypeScript/JS import decomposer  
  - `go.py`: Go import decomposer  
  - `suffix_index.py`: Suffix index builder  
- **Edit `index_service.py`**: Add import resolution phase after parse  
- **DB schema**: Add `import_edges` table (source_file, target_file, imported_names)  
- **MCP Tool**: `resolve_imports(file_path)` — on-demand resolution

## Dependencies
- Pure Python. Uses TreeSitter for parsing import syntax (already available).

## Effort Breakdown
- `import_resolvers/`: ~400 lines across 5+ files  
- Edit `index_service.py`: ~80 lines  
- DB migration: ~15 lines  
- Tests: ~150 lines  
- **Total: ~10 hours**
