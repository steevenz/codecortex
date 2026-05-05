# CodeCortex Architectural Insight · codecortex
> Generated: 2026-05-04 22:39:00

## 1. System Vitality
| Metric | Value |
| :--- | :--- |
| Total Files | 0 |
| God Nodes | 10 |
| Communities | 186 |
| Cohesion Score | N/A |

## 2. Central Hubs (God Nodes)
High-impact files with massive influence over the system architecture.

| Node | Impact | In/Out | centraliy |
| :--- | :--- | :--- | :--- |
| `ab1a287b-30fc-44c1-abdc-c1aaf6f45df3` | 🟡 Significant | 56/0 | 0.0222 |
| `404608c2-0530-4e0d-a710-1dc25579037d` | 🟡 Significant | 51/0 | 0.0144 |
| `313e4e74-2bca-4ea2-be67-79c7ac80b34a` | 🟡 Significant | 44/3 | 0.0048 |
| `0cf6c7e7-ba98-4a9a-b5c1-4ff7a4492a8c` | 🟡 Significant | 44/1 | 0.0048 |
| `420e03b3-2b02-4ba7-aea5-c4bae27651ee` | 🟡 Significant | 44/1 | 0.0048 |

## 3. Temporal Hotspots (Git History)
Files with the highest churn rate. Often indicate technical debt or high-complexity areas.

| File Path | Commit Count | Impact |
| :--- | :--- | :--- |
| `/README.md` | 17 | ⚡ Moderate |
| `/.gitignore` | 4 | ⚡ Moderate |
| `/pyproject.toml` | 4 | ⚡ Moderate |
| `/uv.lock` | 2 | ⚡ Moderate |
| `/requirements.txt` | 2 | ⚡ Moderate |

## 4. Module Interactions
High-level dependencies between system modules/folders.

| Source Module | Target Module | Weight |
| :--- | :--- | :--- |
| `src\domain\graphify\application` | `src\core\backends` | 428.0 |
| `src\domain\repository\infrastructure` | `src\domain\codeindex\infrastructure\parsers\frameworks` | 253.0 |
| `src\domain\graphify\application` | `src\core` | 109.0 |
| `src\domain\codeindex\infrastructure` | `src\domain\codeindex\infrastructure\parsers\frameworks` | 101.0 |
| `src` | `src\core` | 97.0 |
| `tests` | `src\core` | 78.0 |
| `src\domain\graphify\api` | `src\domain\graphify\application` | 64.0 |
| `src\domain\codeindex\application` | `src\core` | 63.0 |
| `tests` | `src\core\backends` | 60.0 |
| `src\domain\codegraph\api` | `src\core\backends` | 54.0 |

## 5. Structural Risks & Observations
- No immediate structural risks detected. System appears balanced.

## 6. Architectural Inquiry
Questions suggested by the graph topology for deep exploration:

- **What is the single responsibility of ab1a287b-30fc-44c1-abdc-c1aaf6f45df3? It appears to be a massive central hub.**
- **Why is `index_repository` such a critical structural bridge? Changes here may have cascading effects.**
- **Why is `write_repository_graph` such a critical structural bridge? Changes here may have cascading effects.**
- **The graph is split into 178 isolated clusters. Is this intentional decoupling or a missing dependency link?**