# CodeTester: Quality Assurance

> **Domain:** CodeTester
> **Package:** `src/modules/codetester/`
> **Version:** 0.1.0
> **AI Coder Impact:** 5/5 ⭐
> **Production Readiness:** 100% 🎯

## Business Context

CodeTester is the **QA quality gate** for CodeCortex — provides unified test execution, coverage analysis, test discovery, test generation, and failure diagnosis across 28 test framework adapters spanning all major languages and package managers. It enables AI coders to run tests, analyze coverage, discover test structures, generate test code, and diagnose failures with actionable insights.

## Why This Exists

- **Unified QA Interface:** Single `code_tester` tool with 5 actions for all QA operations (run, coverage, discover, generate, diagnose)
- **Multi-Language Support:** 28 test framework adapters covering Python, JavaScript/TypeScript, Go, Rust, Kotlin, Java, PHP, Ruby, Elixir, Dart/Flutter, Swift, Haskell, Perl, .NET/C#, C/C++, and CSS
- **Auto-Detection:** Automatic framework detection from project structure (pyproject.toml, package.json, go.mod, Cargo.toml, etc.)
- **AI Coder Empowerment:** Structured JSON output with test summaries, coverage data, failure analysis, and actionable recommendations
- **Background Execution:** Async mode for long-running test suites with task polling
- **Test Generation:** AST-based test code generation for Python functions with parameter extraction

## Theoretical Foundation

- **AST Parsing:** Python ast module for function extraction and parameter analysis
- **Adapter Pattern:** Unified interface for 28 test framework adapters
- **Framework Detection:** Config file scanning and language-based fallback detection
- **Thread Pool Execution:** Background task execution with async mode support
- **Regex Pattern Matching:** Test name filtering and marker extraction
- **SQLite Persistence:** Task storage and result persistence for background jobs
- **Token Economy:** Auto-truncation via `api_response()` when exceeding token budget

## Architecture

```
src/modules/codetester/
├── api/              → tools.py: code_tester MCP tool with 5 actions
├── services/         → Service classes: DI via constructor, pure use-cases
│   ├── tester.py     → Test orchestration (run, coverage, discover, generate, diagnose)
│   ├── qa.py         → Background task execution with webhooks
│   └── search.py     → Test search functionality
├── core/            → dtos.py: typed DTOs, framework.py: framework detection
└── test_adapters/   → 28 framework-specific adapters (pytest, jest, go_test, etc.)
```

## Domain Boundary

- **Owns:** `code_tester` (MCP tool with 5 actions), `qa_status` (background task polling)
- **Does NOT own:** `qa_run` (deprecated naming)
- **Depends on:** `DatabaseManager`, `FilesystemService` (via coderepository)
- **Consumed by:** MCP layer via `api/tools.py`, CLI via `api/cli.py`

## CLI Architecture Note

The CLI domain is named `codetester` (aliases: `qa`, `tester`). Provides 6 commands for QA operations:

| Command | Description |
|---------|-------------|
| `codecortex qa run <target>` | Run tests with auto-detected or specified framework |
| `codecortex qa coverage <target>` | Generate coverage analysis |
| `codecortex qa discover <target>` | Discover all tests in a project |
| `codecortex qa generate <target>` | Generate test code for a function |
| `codecortex qa diagnose <target>` | Diagnose test failures |
| `codecortex qa status <task_id>` | Check background task status |

All CLI commands use the same DTOs and services as the MCP tools, ensuring consistent behavior across interfaces.

## ~/.aicoders/ Compliance

- **API Standard:** `api_response()` for all tool responses
- **DDD:** `api/` + `services/` + `core/` separation
- **DI:** Constructor injection for all services
- **Boundary:** Data crosses layers only via DTOs
- **Error Handling:** Guard clauses, structured errors with error codes (CT_001, CT_002, CT_404, CT_400, CT_500)
- **Logging:** `CodeCortex.Domain.CodeTester` logger namespace
- **Documentation:** All docs in `docs/features/codetester/`

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| CT_001 | 400 | target_path is required |
| CT_002 | 400 | Invalid action (must be one of: run, coverage, discover, generate, diagnose) |
| CT_404 | 404 | Target path not found |
| CT_400 | 400 | Invalid parameter value |
| CT_500 | 500 | Internal server error |

## 10/10 AI Coder Impact Features

1. **Auto-Detection** — Automatic framework detection from project structure (28 frameworks)
2. **Multi-Action Tool** — Single tool with 5 actions for complete QA workflow
3. **Structured Output** — Rich JSON with test summaries, coverage data, failure analysis
4. **Test Generation** — AST-based test code generation with parameter extraction
5. **Failure Diagnosis** — Root cause analysis with source code context and suggestions
6. **Coverage Recommendations** — Actionable coverage improvement suggestions
7. **Test Discovery** — Discover all tests with markers and categories for selective execution
8. **Background Execution** — Async mode for long-running test suites
9. **Framework Filtering** — Test filtering by markers, names, and categories
10. **Multi-Language Support** — 28 test framework adapters across all major languages

## Token Economy

All responses pass through `api_response()` which auto-truncates data exceeding token budget when `summary_mode=True`.

---

## Related Sub-Features

- [Background Tasks](sub-features/background-tasks/concept.md)
- [Run Action](sub-features/run/concept.md)
- [Coverage Action](sub-features/coverage/concept.md)
- [Discover Action](sub-features/discover/concept.md)
- [Generate Action](sub-features/generate/concept.md)
- [Diagnose Action](sub-features/diagnose/concept.md)

## MCP Tool

### `code_tester`

A consolidated test assistant with 5 standard actions:

| Action | Description |
|--------|-------------|
| `run` | Run tests with auto-detected or specified framework |
| `coverage` | Generate coverage analysis with recommendations |
| `discover` | Discover all tests in a project with markers and categories |
| `generate` | Generate test code for a specific function or symbol |
| `diagnose` | Analyze test failures with root cause and suggestions |

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | Yes | - | One of: "run", "coverage", "discover", "generate", "diagnose" |
| `target_path` | string | Yes | - | Path to project directory or source file |
| `test_framework` | string | No | "auto" | Framework name or "auto" for auto-detection |
| `test_filter` | string | No | null | Filter expression (marker, file pattern, test name) |
| `test_names` | list[string] | No | null | List of specific test names to run |
| `categories` | list[string] | No | null | Test categories (unit, integration, e2e) |
| `coverage_format` | string | No | "summary" | "summary" | "detailed" | "json" |
| `target_symbol` | string | No | null | Symbol/function for test generation (action="generate") |
| `max_duration` | int | No | 300 | Max execution time in seconds (10-600) |
| `async_mode` | boolean | No | false | Run in background (returns task_id) |
| `follow` | boolean | No | false | Wait for async completion |

## Supported Test Frameworks (28)

| Language | Adapters |
|----------|----------|
| Python | pytest, unittest, flake8 |
| JavaScript/TypeScript | jest, vitest, npm, pnpm, yarn |
| Go | go_test |
| Rust | cargo_test |
| Kotlin | kotlin_test |
| Java | maven_test, sbt_test |
| PHP | phpunit |
| Ruby | ruby_test |
| Elixir | elixir_test |
| Dart/Flutter | dart_test, flutter_test |
| Swift | swift_test |
| Haskell | haskell_test |
| Perl | perl_test |
| .NET/C# | dotnet_test |
| C/C++ | ctest |
| CSS | stylelint |

## Flow

```
code_tester(action="run", target_path="tests/", test_framework="auto")
    │
    ▼
  Framework detection (auto or specified)
    │
    ▼
  Execute test via adapter
    │
    ▼
  Parse results → Structured JSON output
    │
    ▼
  Return: summary, individual results, duration, framework
```

## Async Mode

```
code_tester(action="run", target_path="tests/", async_mode=True)
    │
    ▼
  Task created (status: pending) ──> Task ID returned
    │
    ▼
  Background execution in thread pool
    │
    ▼
  Poll task status (if follow=False) or wait (if follow=True)
    │
    ▼
  Full results: summary, results, duration, framework
```
