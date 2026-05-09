# Process Detection (Execution Flow Tracing)

**Domain:** CodeGraph  
**Effort:** High | **Impact:** High | **Priority:** 8

## Current State
CodeCortex builds call graphs but does NOT trace execution flows. No way to answer: "What is the end-to-end flow of handling a user login request?" This is the most unique feature of GitNexus that CodeCortex lacks.

## Proposed Improvement
Port GitNexus's `process-processor.ts` — BFS-based execution flow detection:
1. **Entry Point Discovery**: Use Entry Point Scorer (#3) to find root functions
2. **Forward BFS Trace**: Follow CALLS edges from each entry point with:
   - Max trace depth: 10
   - Max branching: 4 (only follow top-N callees by weight)
   - Cycle detection (visited set)
3. **Grouping & Deduplication**: Group similar traces (same start → same end)
4. **Heuristic Labeling**: "ComponentName → ActionName → Detail"
5. **Process Types**: intra_community vs cross_community

## Architecture
```
detect_processes(graph, config)
  ├── entry_points = score_and_rank(graph)  # from #3
  ├── for each entry_point:
  │     process = bfs_trace(entry_point, graph, MAX_DEPTH=10, MAX_BRANCH=4)
  │     if process.steps >= MIN_STEPS=3: add_to_results()
  ├── deduplicate_similar(processes)
  ├── label_heuristic(processes)
  └── return ProcessDetectionResult

bfs_trace(start_node, graph, max_depth, max_branch)
  ├── queue = [(start_node, 0)]
  ├── visited = set()
  ├── while queue and depth < max_depth:
  │     node, depth = queue.pop()
  │     callees = graph.get_callees(node)[:max_branch]
  │     for callee in callees:
  │         if callee not in visited:
  │             visited.add(callee)
  │             queue.append((callee, depth+1))
  └── return Process(steps=visited, type=...)
```

## Key Changes in CodeCortex
- **`src/domain/codegraph/application/`**: New `process_detector.py`  
- **`analysis report`**: Include top 10 processes  
- **DB schema**: New `processes` table + `process_steps` table (migration)  
- **MCP Tool**: `trace_process(repo_id, entry_point)` — on-demand tracing  
- **Integrate** with Entry Point Scorer (#3) and KnowledgeGraph (#7)

## Dependencies
- Pure Python. Requires #3 (entry point scorer) and #7 (knowledge graph) as prerequisites.

## Effort Breakdown
- `process_detector.py`: ~250 lines  
- DB migration: ~30 lines  
- Edit analysis report: ~50 lines  
- MCP tool: ~40 lines  
- Tests: ~120 lines  
- **Total: ~8 hours**
