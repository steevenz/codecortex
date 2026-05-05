---
name: project-soul
description: Architectural DNA and Thinking Patterns - CodeCortex
version: 1.0.1
last_updated: 2026-05-05
---

# Project Soul - Architectural DNA

## Core Philosophy: The Lego Principle
The project is built on the principle of **Atomic Modularity**. Every component must be:
- **Independent**: Able to function with minimal external knowledge.
- **Injectable**: All dependencies provided via constructor.
- **Testable**: Easily mocked in isolation.

## Architectural Patterns
1. **Modular Monolith**: Organized by domain (Bounded Contexts) within CodeCortex.
2. **Domain-Driven Design (DDD)**: Logic resides in `api/`, `application/`, `core/`, and `infrastructure/`.
3. **Repository Pattern**: Centralized data access via `DatabaseManager`.
4. **Adapter/Wrapper Pattern**: All 3rd-party integrations (TreeSitter, OfficeWorkers) must be wrapped.

## Thinking Patterns
- **Socratic Workflow**: Context research -> 2-3 strategic questions -> Approval gate.
- **Fail-Secure**: Robust error handling in MCP tool execution.
- **Zero Technical Debt**: Prioritize DDD alignment over quick hacks.
- **Context Hygiene**: Obsessive maintenance of `.agents/contexts/working.md`.

## Non-Negotiables
1. **DDD Compliance**: All logic must reside in domain-specific layers.
2. **Zero Upstream**: No reliance on unmanaged external mocks.
3. **English Code**: Identifiers, comments, and docs MUST be in English.
4. **Clean Headers**: Every file must have Aegis Codework attribution.
5. **Redact Sensitive**: Never leak tokens/keys in logs or API responses.
