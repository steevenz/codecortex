# Architecture Audit

> **Source:** `CodeGraphService` — `arch_audit` tool

## Concept

Architecture audit systematically scans for code smells and architectural issues: god classes, dead code, security vulnerabilities, and complexity hotspots.

## Audit Types

### God Nodes

Classes or modules with too many dependencies (incoming OR outgoing edges > threshold).

- **Detection:** Degree centrality (in-degree + out-degree) > threshold (default: 10)
- **Risk:** High — god nodes are bottlenecks; changes to them cascade across the system
- **Recommendation:** Split into domain-specific modules, apply Interface Segregation Principle

### Dead Code

Functions, classes, or variables with zero incoming CALLS or IMPORTS edges.

- **Detection:** Graph nodes with no incoming edges (excluding entry points)
- **Risk:** Medium — dead code increases maintenance burden and confuses new developers
- **Recommendation:** Remove unused code; keep only if explicitly exported as public API

### Security Hygiene

Detection of hardcoded secrets, dangerous patterns, and insecure practices.

- **Detection:** Regex patterns against file content and commit history
- **Patterns:** API keys, passwords, private keys, connection strings, tokens
- **Risk:** Critical — hardcoded secrets in source code are the #1 cause of data breaches

### Cyclomatic Complexity

Functions with excessive branching (if/else, switch, loops).

- **Detection:** AST node counting of control flow statements
- **Threshold:** > 10 branches = complex, > 20 = needs refactoring
- **Risk:** Medium — high complexity = bugs, hard to test, hard to understand

## Combined Output

```json
{
  "god_nodes": [{"name": "Utils", "in_degree": 47, "risk": "high"}],
  "dead_code": [{"name": "legacy_migration", "file": "src/db/migrate.py:12", "risk": "medium"}],
  "security": [{"type": "hardcoded_api_key", "file": "src/config.py:5", "risk": "critical"}],
  "complexity": [{"name": "parse_config", "complexity": 25, "file": "src/utils/parser.py:30", "risk": "high"}]
}
```
