# MCP-Neocortex Bridge Improvement Plan

**Date**: 2026-06-01  
**Project**: CodeCortex MCP Server  
**Status**: Implementation Plan  
**Priority**: High

---

## 1. Implementation Roadmap

### Phase 1: Critical Fixes (P0 - Immediate)

| Task | File | Description | Effort |
|------|------|-------------|--------|
| Create CodeCortexClient | `src/core/bridges/codecortex_client.py` | Implement missing bidirectional client | 2 days |
| Add Circuit Breaker | `src/core/cognitive/bridge.py` | Add circuit breaker to bridge calls | 1 day |
| Add Retry Logic | `src/core/cognitive/bridge.py` | Implement exponential backoff retry | 1 day |

### Phase 2: Performance Enhancements (P1 - Short-term)

| Task | File | Description | Effort |
|------|------|-------------|--------|
| Connection Pooling | `src/core/cognitive/bridge.py` | Reuse HTTP connections | 1 day |
| Configurable Timeouts | `src/core/cognitive/bridge.py` | Environment-based timeout config | 0.5 day |
| Payload Validation | `src/core/cognitive/bridge.py` | Add size limits | 0.5 day |

### Phase 3: Observability (P2 - Medium-term)

| Task | File | Description | Effort |
|------|------|-------------|--------|
| Structured Logging | `src/core/cognitive/bridge.py` | Add request_id and metrics | 1 day |
| Health Endpoint | `src/api/orchestration.py` | Add bridge health check | 0.5 day |
| Metrics Export | New file | Prometheus metrics | 2 days |

---

## 2. Detailed Implementation Steps

### 2.1 CodeCortexClient Implementation

**File**: `src/core/bridges/codecortex_client.py`

```python
class CodeCortexClient:
    """Client for Neocortex to call back into CodeCortex."""
    
    def __init__(self):
        self.transport_mode = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_TRANSPORT", "sse")
        self.codecortex_url = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_URL", "http://127.0.0.1:8001")
        self.api_key = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_API_KEY", "")
    
    async def get_code_context(self, query: str, repo_path: str):
        """Search codebase context."""
        
    async def get_architecture(self, repo_path: str):
        """Get architecture audit."""
        
    async def query_docs(self, query: str, repo_path: str):
        """Query documentation."""
```

**Environment Variables**:
```bash
NEOCORTEX_BRIDGE_CODECORTEX_URL=http://127.0.0.1:8001
NEOCORTEX_BRIDGE_CODECORTEX_API_KEY=<key>
NEOCORTEX_BRIDGE_CODECORTEX_TRANSPORT=sse
```

---

### 2.2 Circuit Breaker Implementation

**Location**: `src/core/cognitive/bridge.py` (already added)

**Configuration**:
```bash
CODECORTEX_BRIDGE_CIRCUIT_THRESHOLD=5      # Failure threshold
CODECORTEX_BRIDGE_RECOVERY_TIMEOUT=60      # Recovery timeout in seconds
```

---

### 2.3 Retry Logic Implementation

**Location**: `src/core/cognitive/bridge.py` (already added)

**Configuration**:
```bash
CODECORTEX_BRIDGE_MAX_RETRIES=3            # Max retry attempts
CODECORTEX_BRIDGE_RETRY_BASE_DELAY=1.0     # Base delay in seconds
CODECORTEX_BRIDGE_RETRY_MAX_DELAY=10.0     # Max delay in seconds
```

---

### 2.4 Connection Pooling

**Location**: `src/core/cognitive/bridge.py` (already added)

**Configuration**:
```bash
CODECORTEX_BRIDGE_POOL_CONNECTIONS=10      # Max keepalive connections
CODECORTEX_BRIDGE_POOL_MAX_CONNECTIONS=100 # Max total connections
```

---

### 2.5 Timeout Configuration

**Location**: `src/core/cognitive/bridge.py` (already added)

**Configuration**:
```bash
CODECORTEX_BRIDGE_REST_TIMEOUT=60.0        # REST endpoint timeout
CODECORTEX_BRIDGE_MCP_TIMEOUT=30.0         # MCP endpoint timeout
CODECORTEX_BRIDGE_MAX_PROMPT_SIZE=10000    # Max prompt size before truncation
```

---

## 3. Test Verification

### 3.1 Run Tests
```bash
pytest tests/e2e/test_bridge_neocortex.py -v
```

### 3.2 Expected Results

| Test Suite | Expected |
|------------|----------|
| Functional Tests | 100% pass |
| Latency Tests | All under thresholds |
| Resilience Tests | Graceful failure handling |
| Data Integrity | No data loss |
| Security Tests | Keys not leaked |

---

## 4. Rollback Plan

If issues arise:

1. Revert to original `bridge.py` from git
2. Remove `codecortex_client.py`
3. Set environment variable `CODECORTEX_BRIDGE_ENABLED=false` to disable bridge

---

## 5. Post-Implementation Checklist

- [ ] CodeCortexClient created and tested
- [ ] Circuit breaker integrated
- [ ] Retry logic working
- [ ] Connection pooling active
- [ ] Configurable timeouts verified
- [ ] Structured logging implemented
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Environment variables documented

---

## 6. Dependencies

- `httpx` - Already in pyproject.toml
- `circuitbreaker` - Already in pyproject.toml
- `tenacity` - Need to add to pyproject.toml

### Add to pyproject.toml:
```toml
[project.dependencies]
tenacity = ">=8.0.0"
```

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Bridge Discovery | < 500ms | pytest latency test |
| LLM Enrichment | < 5s | Integration test |
| Failure Recovery | 100% | Resilience test |
| Error Rate | < 1% | Production logs |
| Circuit Breaker | Triggers at 5 failures | Unit test |

---

**Prepared by**: AI Bridge Assessment  
**Review**: Pending  
**Approved**: Pending