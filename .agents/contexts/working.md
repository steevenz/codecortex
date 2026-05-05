---
Version: 1.2.0
Date: 2026-05-05
---

# Working Context - CodeCortex MCP & Standard Alignment

## Current Truth
- **Active Task**: Aligning CodeCortex with new Aegis .agents standards and hardening MCP infrastructure.
- **Project Root**: `c:\Users\steevenz\.aicoders\scripts\pythons\codecortex`
- **Core Status**:
    - **Infrastructure Hardened**: SSE transport, Port locking (Node.js Proxy), and Secret pathing implemented.
    - **Persistence**: Hub-and-Spoke database architecture active.
    - **Standards Migration**: Transitioning from legacy `SOUL.md`/`WORKING-CONTEXT.md` to `.agents/contexts/` structure.
- **Transport**: `http-jsonrpc/sse` with standard stdio fallback.

## Context Gap
- **Domain Refactoring**: `codegraph` and `codeindex` still need full internal layering refactor.
- **Pydantic Migration**: Boundary DTOs not yet fully implemented.
- **Documentation**: Need to migrate remaining legacy docs to the new hierarchy.

## Done List
- [x] Implemented Shared Server Proxy (`index.js`) with port locking.
- [x] Hardened `http_server.py` with SSE, Redaction, and Secure Pathing.
- [x] Updated `main.py` for transport flexibility.
- [x] Created `.agents/contexts/principal.md` (Project Soul).
- [x] Initialized `.agents/contexts/working.md`.

## Target Queue
1. [ ] Remove legacy `SOUL.md` and `WORKING-CONTEXT.md` after verification.
2. [ ] Standardize `CodeGraph` domain structure and refactor Mixins.
3. [ ] Standardize `CodeIndex` domain structure.
4. [ ] Implement Pydantic models for all tool boundaries.
5. [ ] Perform final validation of SSE transport with multi-client access.
