# Heritage Extraction (Class Hierarchy)

**Domain:** CodeGraph  
**Effort:** High | **Impact:** Medium | **Priority:** 10

## Current State
CodeCortex extracts symbols including classes, but does NOT extract inheritance hierarchies. No ability to answer:
- "What interfaces does this class implement?"
- "What is the full class hierarchy?"
- "Which methods are inherited vs overridden?"

## Proposed Improvement
Port GitNexus's heritage extraction system:
1. **Heritage Extraction per language**: Parse class definitions for `extends`, `implements`, `inherits` keywords
   - Python: `class Foo(Base)` → `{parent: "Base", type: "inheritance"}`
   - TypeScript: `class Foo extends Bar implements Baz` → `{parent: "Bar", interfaces: ["Baz"]}`
   - Java: `class Foo extends Bar implements Baz` → same pattern
   - Go: `type Foo struct { Bar }` → `{parent: "Bar", type: "embedding"}`
2. **Heritage Map**: `Map<className, HeritageInfo>` with multi-parent support
3. **MRO Computation**: Method Resolution Order for OOP languages
4. **Graph Edges**: Store as INHERITS edges in KnowledgeGraph

## Architecture
```
extract_heritage(files, parse_results)
  ├── for each class symbol:
  │     heritage = parse_heritage_declaration(node, language)
  │     heritage_map[class_name] = heritage
  ├── resolve_cross_file_parents(heritage_map, symbol_table)
  ├── compute_mro(heritage_map)  # C3 linearization for Python
  └── return HeritageResult {heritage_map, mro_map, edges}

parse_heritage_declaration(node, language):
  ├── Python: walk class_definition → base_clauses
  ├── TS/JS: walk class_declaration → heritage_clauses
  ├── Java: walk class_declaration → type_parameters
  └── ... (per language)
```

## Key Changes in CodeCortex
- **`src/domain/codegraph/application/`**: New `heritage_extractor.py`  
- **`src/domain/codeindex/infrastructure/`**: Per-language heritage parsers  
  - `heritage_python.py`  
  - `heritage_typescript.py`  
  - `heritage_java.py`  
- **Edit `codegraph_service.py`**: Add heritage extraction phase  
- **DB**: Edges already support `INHERITS` type — just populate  
- **MCP Tool**: `get_class_hierarchy(class_name)` — on-demand query

## Dependencies
- Pure Python. Uses TreeSitter (already available).

## Effort Breakdown
- `heritage_extractor.py`: ~150 lines  
- Per-language parsers: ~200 lines  
- Edit `codegraph_service.py`: ~50 lines  
- Tests: ~100 lines  
- **Total: ~6 hours**
