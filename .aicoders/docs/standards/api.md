# API Standard (MCP Tools)

> **Standard:** CODDY-API-v1.0
> **Applies to:** All MCP tools in CodeCortex

## 1. Tool Registration

```python
def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    _build_tools(mcp, orchestrator_factory)
```

## 2. Response Format

ALL tool responses MUST use `api_response()`:

```python
api_response(success, status_code, message, data, request_id, error_code=None, insight=None)
```

## 3. Error Code Standard

| Pattern | Example | Severity |
|---------|---------|----------|
| `{DOMAIN}_001` | `KG_001` | High (validation) |
| `{DOMAIN}_002` | `KG_002` | High (not found) |
| `{DOMAIN}_500` | `KG_500` | Critical (internal) |
| `{DOMAIN}_{NAME}_ERROR` | `KG_EXTRACT_ERROR` | Critical (CLI) |

## 4. Parameter Standard

- Use Python type hints for all parameters
- Optional params MUST have `= None` default
- `limit` MUST be capped at 200
- `repo_path` MUST be validated with `Path.exists()`

## 5. Docstring Standard

```python
"""
@param action: Operation to perform:
  - extract: Description.
    param1 (required): Description.
  - query: Description.
    param2 (required): Description.
@param param1: Description with constraints.
"""
```

## 6. Compliance Checklist

- [ ] `register_tools()` function exported
- [ ] All responses use `api_response()`
- [ ] Error codes follow domain prefix pattern
- [ ] `request_id` used for all requests
- [ ] `limit` capped at 200
- [ ] `orchestrator_factory` parameter accepted
- [ ] All errors caught with try/except
- [ ] DB closed in `finally` block
