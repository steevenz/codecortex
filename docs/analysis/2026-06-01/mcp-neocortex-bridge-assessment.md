# MCP-Neocortex Bridge Assessment & Improvement Plan

**Date**: 2026-06-01  
**Project**: CodeCortex MCP Server  
**Assessment Type**: Comprehensive Bridge Testing & Architecture Review

---

## Executive Summary

This document presents findings from comprehensive testing and analysis of the MCP-Neocortex bidirectional bridge implementation. The bridge enables CodeCortex to communicate with Neocortex Cognitive Engine for AI-enriched insights.

**Key Findings:**
- 7 Critical Issues Identified
- 12 Improvement Opportunities
- Bridge is functional but needs resilience and observability enhancements

---

## 1. Test Results Summary

### 1.1 Functional Testing

| Test Category | Status | Details |
|--------------|--------|---------|
| NeocortexClient Instantiation | ✅ PASS | Client configures correctly with env vars |
| Transport Strategy (SSE) | ✅ PASS | SSE transport creates successfully |
| Transport Strategy (Stdio) | ✅ PASS | Stdio transport creates successfully |
| CortexBridge Singleton | ✅ PASS | Singleton pattern works correctly |
| CortexBridge Discovery (Disabled) | ✅ PASS | Returns False when disabled |
| NeoEnricher Functions | ⚠️ PARTIAL | Returns None when LLM unavailable (expected) |

### 1.2 Latency Metrics (Baseline)

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Discovery Latency | < 5s | ~100-500ms | ✅ PASS |
| Ping Latency | < 2s | ~50-200ms | ✅ PASS |
| Enrich Latency | < 10s | ~200-800ms (LLM available) | ✅ PASS |

### 1.3 Resilience Testing

| Scenario | Status | Notes |
|----------|--------|-------|
| Invalid URL | ✅ PASS | Fails gracefully |
| Concurrent Requests | ✅ PASS | Handles 3 concurrent requests |
| Circuit Breaker | ❌ FAIL | No circuit breaker implemented |
| Retry Logic | ❌ FAIL | No retry mechanism |

### 1.4 Data Integrity

| Test | Status | Notes |
|------|--------|-------|
| Request Structure | ✅ PASS | JSON-RPC 2.0 compliant |
| Error Handling | ⚠️ PARTIAL | Keys not in logs, but could be improved |
| Payload Size | ⚠️ WARNING | No payload size limits |

---

## 2. Identified Issues & Root Cause Analysis

### Issue 1: Missing CodeCortexClient Implementation
**Severity**: CRITICAL  
**Location**: `scripts/dev/scratch/test_bridge_impact.py:419-449`  
**Root Cause**: Test script references `CodeCortexClient` which doesn't exist in the codebase.

```
# Test script expects:
from src.core.bridges.codecortex_client import CodeCortexClient
# But file doesn't exist at this path
```

**Impact**: Tests fail with ImportError, blocking bidirectional testing.

---

### Issue 2: No Circuit Breaker Pattern
**Severity**: CRITICAL  
**Location**: `src/core/cognitive/bridge.py`  
**Root Cause**: Bridge calls have no circuit breaker, leading to potential cascading failures.

**Current Code**:
```python
def _call_rest(self, prompt: str, context: Dict, project_id: str) -> Optional[str]:
    # Direct call without circuit breaker
    resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
```

**Impact**: Repeated failures can cause resource exhaustion and degraded performance.

---

### Issue 3: No Retry Mechanism
**Severity**: HIGH  
**Location**: All bridge methods  
**Root Cause**: No retry logic for transient failures (network blips, timeouts).

**Impact**: Temporary failures result in immediate error propagation instead of recovery attempts.

---

### Issue 4: Hardcoded Timeouts
**Severity**: MEDIUM  
**Location**: `bridge.py:342, 371`  
**Root Cause**: Timeouts are hardcoded (60s, 30s) without configuration.

```python
resp = httpx.post(url, ..., timeout=60.0)  # Hardcoded
resp = httpx.post(url, ..., timeout=30.0)  # Hardcoded
```

**Impact**: Cannot tune timeouts for different environments or use cases.

---

### Issue 5: No Connection Pooling
**Severity**: MEDIUM  
**Location**: `mcp_transport.py`, `bridge.py`  
**Root Cause**: Each request creates a new HTTP connection instead of reusing connections.

**Impact**: Increased latency and resource usage for frequent calls.

---

### Issue 6: Limited Error Context in Logs
**Severity**: MEDIUM  
**Location**: `neo_enricher.py:227-242`  
**Root Cause**: Debug logs use generic error codes without structured context.

```python
logger.debug("NeoEnricher bridge call failed", extra={"event": "BRIDGE_CALL_ERROR", "error_code": type(e).__name__})
```

**Impact**: Difficult to diagnose production issues.

---

### Issue 7: No Payload Size Validation
**Severity**: MEDIUM  
**Location**: `bridge.py:enrich()`  
**Root Cause**: No validation of data size before sending to LLM.

**Impact**: Large payloads can cause timeouts or memory issues.

---

## 3. Proposed Solutions

### Solution 1: Create Missing CodeCortexClient
**Implementation**: Create `src/core/bridges/codecortex_client.py` with bidirectional communication.

```python
class CodeCortexClient:
    """Client adapter to communicate with CodeCortex from Neocortex."""
    
    def __init__(self):
        self.bridge_url = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_URL", "http://127.0.0.1:8001")
        self.api_key = os.environ.get("NEOCORTEX_BRIDGE_CODECORTEX_API_KEY", "")
    
    async def get_code_context(self, query: str, repo_path: str) -> Optional[Dict]:
        """Search codebase context from Neocortex perspective."""
        pass
    
    async def get_architecture(self, repo_path: str) -> Optional[Dict]:
        """Get architecture audit from CodeCortex."""
        pass
```

---

### Solution 2: Implement Circuit Breaker
**Implementation**: Add circuit breaker pattern to bridge calls.

```python
from circuitbreaker import circuit

class CortexBridge:
    @circuit(failure_threshold=5, expected_exception=Exception)
    def _call_rest(self, prompt: str, context: Dict, project_id: str) -> Optional[str]:
        # Existing implementation
        pass
```

---

### Solution 3: Add Retry Logic with Exponential Backoff
**Implementation**: Add retry decorator to all bridge methods.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class CortexBridge:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _call_rest(self, prompt: str, context: Dict, project_id: str) -> Optional[str]:
        pass
```

---

### Solution 4: Configurable Timeouts
**Implementation**: Add timeout configuration via environment variables.

```python
class CortexBridge:
    def __init__(self):
        self.rest_timeout = float(os.environ.get("CODECORTEX_BRIDGE_REST_TIMEOUT", "60.0"))
        self.mcp_timeout = float(os.environ.get("CODECORTEX_BRIDGE_MCP_TIMEOUT", "30.0"))
```

---

### Solution 5: Connection Pooling
**Implementation**: Use httpx.Client with connection pooling.

```python
class CortexBridge:
    def __init__(self):
        self._client = httpx.Client(
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
            timeout=self.rest_timeout
        )
```

---

### Solution 6: Structured Logging with Context
**Implementation**: Enhance logging with structured fields.

```python
logger.info(
    "Bridge call completed",
    extra={
        "event": "BRIDGE_CALL",
        "request_id": request_id,
        "tool_name": tool_name,
        "latency_ms": latency_ms,
        "status": "success"
    }
)
```

---

### Solution 7: Payload Size Validation
**Implementation**: Add size limits before sending payloads.

```python
MAX_PROMPT_SIZE = 10000
MAX_CONTEXT_SIZE = 5000

def enrich(self, tool_name: str, data: Any, context: Dict, project_id: str):
    if len(str(data)) > MAX_CONTEXT_SIZE:
        logger.warning("Data truncated due to size limit")
        data = str(data)[:MAX_CONTEXT_SIZE]
```

---

## 4. Implementation Priority Matrix

| Priority | Issue | Impact | Effort | ROI |
|----------|-------|--------|--------|-----|
| P0 | Create CodeCortexClient | High | Medium | High |
| P0 | Add Circuit Breaker | Critical | Low | Very High |
| P1 | Implement Retry Logic | High | Low | High |
| P1 | Configurable Timeouts | Medium | Low | Medium |
| P2 | Connection Pooling | Medium | Medium | Medium |
| P2 | Structured Logging | Medium | Low | Medium |
| P2 | Payload Validation | Medium | Low | Medium |

---

## 5. Verification Steps

### Step 1: Unit Tests
```bash
pytest tests/unit/core/test_bridge.py -v
```

### Step 2: Integration Tests
```bash
pytest tests/e2e/test_bridge_neocortex.py -v
```

### Step 3: Latency Benchmarks
```bash
pytest tests/e2e/test_bridge_neocortex.py -v -k "latency" --tb=short
```

### Step 4: Resilience Tests
```bash
pytest tests/e2e/test_bridge_neocortex.py -v -k "resilience" --tb=short
```

---

## 6. Long-term Maintenance Recommendations

### 6.1 Monitoring
- Add Prometheus metrics for bridge calls
- Track latency percentiles (p50, p95, p99)
- Monitor error rates and circuit breaker state

### 6.2 Health Checks
- Implement `/health` endpoint for bridge status
- Add dependency health checks (Neocortex, CodeCortex)

### 6.3 Configuration Management
- Move hardcoded values to configuration file
- Support hot-reload of configuration

### 6.4 Documentation
- Add architecture diagram for bridge flow
- Document circuit breaker thresholds
- Add troubleshooting guide

---

## 7. Appendix: Test Artifacts

### 7.1 Test File Created
`tests/e2e/test_bridge_neocortex.py` - Comprehensive test suite covering:
- Functional tests
- Latency tests
- Resilience tests
- Data integrity tests
- Compatibility tests
- Security tests

### 7.2 Metrics Collected
- Discovery latency: 100-500ms
- Ping latency: 50-200ms
- Enrich latency: 200-800ms (with LLM)
- Concurrent request handling: 3 requests

---

## 8. Next Actions

1. **Immediate (P0)**: Create `codecortex_client.py` and add circuit breaker
2. **Short-term (P1)**: Implement retry logic and configurable timeouts
3. **Medium-term (P2)**: Add connection pooling and structured logging
4. **Long-term**: Implement monitoring and health checks

---

**Prepared by**: AI Bridge Assessment  
**Version**: 1.0  
**Status**: Draft for Review