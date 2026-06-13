---
description: CCT Deep Reasoning — leverage Creative Critical Thinking for complex architecture and design decisions
title: WFK_CCT_001 — CCT Deep Reasoning
workflow_id: WFK_CCT_001
version: 1.0.0
author: Steeven Andrian
standard: CODDY-Workflow-v2.0
---

# WFK_CCT_001: CCT Deep Reasoning

> **Goal**: Use the Creative Critical Thinking (CCT) proxy for complex architectural decisions, trade-off analysis, and multi-domain reasoning that exceeds simple tool chaining.
> **Trigger**: User asks a "should I" question, needs architecture advice, or faces a complex design decision.
> **Time**: 30s to 2 minutes (CCT server latency).
> **Cost**: High (LLM reasoning, token-intensive).
> **Important**: CCT is **CLI-only** — it proxies to the CCT cognitive server, not available as an MCP tool.
> **Codification**: CODDY-Architecture-v1.0 §5 — `WFK_CCT_001`

---

## 1. Trigger Phrases

- *"Should I use X or Y?"*
- *"Architecture decision"*
- *"Trade-off analysis"*
- *"Evaluate this design"*
- *"Which approach is better?"*
- *"Complex multi-domain problem"*
- *"Hard refactoring strategy"*
- *"Security vs performance trade-off"*
- *"Framework selection"*
- *"Review this approach"*

---

## 2. Why CCT is CLI-Only

CCT (Creative Critical Thinking) is **not exposed as an MCP tool** because:

1. **Long-running reasoning**: CCT sessions can take 30-120 seconds — too slow for real-time MCP tool calls.
2. **Stateful sessions**: CCT maintains a thinking context across multiple prompts.
3. **LLM-backed**: CCT uses its own LLM instance for deep reasoning, separate from the agent's LLM.
4. **Project tracking**: CCT tracks reasoning projects separately from CodeCortex repos.

**Rule**: When user needs deep reasoning → **always use CLI `cct` subcommand**.

---

## 3. Pipeline Overview

```
Step 1: Think-Start  (cct:think-start)   ───┐
Step 2: Analyze       (cct:analyze)       ───┤───► Deliverable
Step 3: Code Context  (cct:code-analyze) ───┤
Step 4: Synthesize    (AI + CCT output)   ───┘
```

---

## 4. Step 1 — Think-Start (Initiate Reasoning Session)

**Purpose**: Start a CCT reasoning project for a complex problem.

### CLI Call
```bash
codecortex neocortex think-start "Should we use event sourcing or CRUD for the order module?" \
  --profile critical \
  --project-id OrderService \
  --reasoning-depth deep
```

### Parameters
| Parameter | Required | Options | Description |
|-----------|----------|---------|-------------|
| `question` | Yes | — | The core decision/problem |
| `--profile` | No | `standard`, `critical`, `exploratory` | Reasoning intensity |
| `--project-id` | No | — | Associates reasoning with a project |
| `--reasoning-depth` | No | `shallow`, `standard`, `deep` | How many reasoning layers |

### Response Fields
```json
{
  "project_id": "OrderService",
  "session_id": "sess_abc123",
  "thinking_status": "active",
  "initial_insights": [
    "Event sourcing adds complexity but enables audit trails",
    "CRUD is simpler but loses historical state"
  ],
  "recommendation": "Start with CRUD, add event sourcing incrementally if audit requirements grow"
}
```

---

## 5. Step 2 — Analyze (Evaluate Specific Context)

**Purpose**: Feed real codebase context into the CCT reasoning session.

### CLI Call
```bash
codecortex neocortex analyze "Evaluate the coupling between PaymentService and InventoryService" \
  --repo-path /path/to/project \
  --format insight \
  --project-id OrderService
```

### Parameters
| Parameter | Required | Description |
|-----------|----------|-------------|
| `question` | Yes | Specific analysis target |
| `--repo-path` | Yes | Path to codebase for context |
| `--format` | No | `insight`, `detailed`, `actionable` |
| `--project-id` | No | Links to existing thinking session |

---

## 6. Step 3 — Code Context (CCT-Enhanced Code Analysis)

**Purpose**: Use CCT's specialized code understanding to analyze patterns.

### CLI Call
```bash
codecortex neocortex code-analyze "Evaluate the authentication flow in this codebase" \
  --repo-path /path/to/project \
  --project-id OrderService
```

### CLI Alternative: Code Search via CCT
```bash
codecortex neocortex code-search "event handling patterns" \
  --repo-path /path/to/project \
  --limit 10 \
  --project-id OrderService
```

---

## 7. Step 4 — Synthesize

**Purpose**: Combine CCT reasoning output with CodeCortex tool findings.

### Synthesis Pattern
```
1. CCT provides: reasoning, trade-offs, recommendations
2. CodeCortex provides: actual code metrics, graph data, test results
3. AI synthesizes: actionable decision with evidence

Example:
  CCT says: "Consider event sourcing for audit requirements"
  CodeCortex graph shows: OrderService has 45 callers (god node)
  CodeCortex audit shows: No existing event infrastructure

  Synthesis: "Defer event sourcing. Current OrderService is already complex
    (45 callers). Add audit logging to existing CRUD first. Revisit event
    sourcing in Q3 when coupling is reduced."
```

---

## 8. CCT vs CodeCortex — When to Use Which

| Task | Use | Why |
|------|-----|-----|
| "Should I use microservices or monolith?" | **CCT** | Subjective trade-off, needs reasoning |
| "How many callers does ServiceX have?" | **CodeCortex** | Factual, graph query |
| "Is this code production ready?" | **CodeCortex** | Objective metrics, 7-gate checklist |
| "What's the blast radius of this refactor?" | **CodeCortex** | `cb:refactor:impact` |
| "Event sourcing vs CQRS for our domain?" | **CCT** | Complex architectural decision |
| "Find all usages of this function" | **CodeCortex** | `cb:graph:query callers` |
| "Security vs performance for auth layer?" | **CCT + CodeCortex** | CCT for trade-off, CodeCortex for actual metrics |

---

## 9. Deliverable Format

```markdown
# CCT Reasoning Report

## 1. Question
> "<the original question>"

## 2. CCT Reasoning Summary
- **Profile**: <critical/standard/exploratory>
- **Key Insights**:
  1. <insight 1>
  2. <insight 2>
- **CCT Recommendation**: <recommendation>

## 3. CodeCortex Evidence
| Metric | Value | Implication |
|--------|-------|-------------|
| <metric> | <value> | <what it means> |

## 4. Synthesized Decision
**Recommendation**: <clear actionable recommendation>
**Confidence**: <high/medium/low>
**Evidence**: <citations from both CCT and CodeCortex>
**Next Steps**: <specific actions>

## 5. Risks & Mitigations
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| ... | ... | ... |
```

---

## 10. Anti-Patterns

| Anti-Pattern | Why It's Wrong | Correct Approach |
|-------------|----------------|----------------|
| Use CCT for simple factual lookups | Wastes tokens and time | Use `cb:search` or `cb:graph:query` |
| Use CCT without CodeCortex context | CCT hallucinates code state | Always provide `--repo-path` |
| Ignore CCT recommendation blindly | CCT is advisory, not authoritative | Validate with CodeCortex metrics |
| Start CCT for every question | Expensive and slow | Reserve for complex architectural decisions |

---

## 11. AI Coder Optimization Guide

### Token Economy
| Technique | Token Saved | How |
|-----------|-------------|-----|
| Always run CodeCortex tools BEFORE CCT | ~50% | CCT with real data > CCT hallucinating |
| `reasoning-depth: shallow` for simple decisions | ~40% | Don't run deep reasoning for trivial choices |
| Batch multiple questions into one `think-start` | ~30% | One CCT session vs multiple |
| `--format insight` vs `detailed` | ~25% | Shorter output, faster parsing |

### Parallel Execution
- CCT is inherently sequential (thinking sessions build on each other)
- But CodeCortex context gathering (`cb:status`, `cb:audit`) can run in parallel with CCT initialization
- `cct:analyze` and `cct:code-search` can run in parallel if independent

### Early Exit Conditions
| Condition | Action |
|-----------|--------|
| CodeCortex audit already answers the question | Skip CCT entirely, deliver tool results |
| User asks "what is the cyclomatic complexity of X?" | Use `cb:analyze` directly, no CCT |
| `cb:graph:query` shows clear answer | Skip CCT, graph data is factual |
| CCT returns "insufficient data" | Abort CCT, gather more CodeCortex data first |

### Cache Reuse
- CCT `project_id` persists reasoning context across sessions
- CodeCortex `repo_id` and graph are the same regardless of CCT session
- Reuse previous CCT analysis for same architectural question if code unchanged

---

*Cross-reference: [workflow-index.md](workflow-index.md) | [deep-analysis-workflow.md](deep-analysis-workflow.md)*
