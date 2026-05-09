# Framework Detection

> **Source:** `src/domain/codeindex/infrastructure/frameworks.py`
> **Detectors:** `src/domain/codeindex/infrastructure/parsers/frameworks/`

## Concept

Framework detection identifies which web frameworks a codebase uses. This enables framework-aware analysis: a function can be tagged as "FastAPI route handler" or "React component" rather than a generic function.

## Detected Frameworks

| Framework | Detector | Detection Method |
|-----------|----------|-----------------|
| **Next.js** | `nextjs.py` | File patterns (`pages/`, `app/`), `'next'` in imports, `getServerSideProps` exports |
| **React** | `react.py` | `from 'react'` imports, JSX usage, hooks (`useState`, `useEffect`) |
| **Flutter** | `flutter.py` | `from 'flutter'` imports, `extends StatelessWidget` / `extends StatefulWidget` |
| **Laravel** | `laravel.py` | File structure (`app/Http/Controllers/`), facades, `Illuminate` namespace |
| **FastAPI** | (built-in to graph tools) | `@app.get/post/...` decorators, `from fastapi import` |
| **Django** | (built-in to graph tools) | `from django import`, `models.Model` inheritance |
| **Express** | (built-in to graph tools) | `require('express')`, `app.get/post/...` calls |

## Output

Framework metadata is attached to symbols as `framework` attribute:

```json
{
  "name": "LoginPage",
  "symbol_type": "function",
  "framework": "nextjs",
  "metadata": {
    "decorators": ["@withAuth"],
    "is_page": true,
    "is_api_route": false
  }
}
```
