# Route Extraction

> **Source:** Integrated into `CodeGraphService`

## Concept

Route extraction identifies HTTP route handlers and their URL patterns, HTTP methods, and middleware. This enables the LLM to understand the API surface of a web application without reading router configuration files.

## Supported Frameworks

| Framework | Detection Pattern | Extracted Info |
|-----------|------------------|----------------|
| **FastAPI** | `@router.get/post/put/delete(...)` | Path, method, response_model, dependencies |
| **Django** | `path(...)`, `re_path(...)` in `urls.py` | URL pattern, view function, name |
| **Flask** | `@app.route(...)` | URL rule, methods, endpoint |
| **Express** | `app.get/post/put/delete(...)` | Path, handler, middleware |
| **Next.js** | File-based (`pages/api/*`) + `app/api/*` | Route path, HTTP method, handler export |

## Output

```json
{
  "routes": [
    {
      "path": "/api/users/{user_id}",
      "method": "GET",
      "handler": "get_user",
      "file": "src/api/users.py:42",
      "framework": "fastapi",
      "middleware": ["@requires_auth", "@rate_limit"],
      "response_model": "UserResponse"
    },
    {
      "path": "/api/users",
      "method": "POST",
      "handler": "create_user",
      "file": "src/api/users.py:55",
      "framework": "fastapi",
      "response_model": "UserResponse",
      "status_code": 201
    }
  ]
}
```

## Impact

Route extraction allows the LLM to:
- Map URL paths to handler code instantly
- Understand the API contract (request/response models)
- Know which middleware applies to which routes
- Detect undocumented endpoints


---

## Error Codes

| Prefix | Tool | Description |
|--------|------|-------------|
| RE_001 | graph_analyze (route_extraction) | Route pattern not recognized |
| RE_002 | graph_analyze (route_extraction) | Framework-specific extraction failed |

---

## Performance

- **Time Complexity:** O(N) for scanning route files
- **Regex Cost:** Pattern matching is linear in file size
- **Memory Usage:** O(R) for storing route metadata
- **Optimization:** Incremental scan based on file modification time
