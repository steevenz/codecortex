# Framework Detection

> **Source:** `src/domain/coderepository/infrastructure/detector.py` -> `RepositoryFrameworkDetector`
> **Integration:** `src/domain/codeindex/application/service.py` -> `_enrich_frameworks()`
> **Per-Language Detectors:** `src/domain/codeindex/infrastructure/parsers/frameworks/`

## Concept

Framework detection identifies which web/mobile frameworks a codebase uses. This enables framework-aware analysis: a function can be tagged as "React component" or "FastAPI route handler" rather than a generic function.

## Architecture

```
index_repository()
    |
    v
  _enrich_frameworks(file_path, parsed, repo_id, repo_root)
    |
    +-- RepositoryFrameworkDetector.get_or_create(repo_root)
    |     +-- Cached per repo_id in _repo_detector_cache dict (bounded to 20 entries)
    |
    +-- RepositoryFrameworkDetector.enrich_file(rel_path, source, imports, classes, functions)
          |
          +-- Returns: {"frameworks": ["react", "nextjs"], ...}
```

Unlike file-level detection, `RepositoryFrameworkDetector` uses **repository-level context** -- it detects frameworks from configuration files (`package.json`, `composer.json`, etc.) and confirms via file-level signals.

## Detected Frameworks

| Framework | Detector File | Detection Method |
|-----------|--------------|-----------------|
| **Next.js** | `nextjs.py` | File patterns (`pages/`, `app/`), `'next'` imports, `getServerSideProps` exports |
| **React** | `react.py` | `from 'react'` imports, JSX usage, hooks (`useState`, `useEffect`) |
| **Vue** | `vue.py` | `.vue` SFC detection, Vue imports |
| **Angular** | `angular.py` | `@Component`, `@NgModule` decorators, `angular.json` |
| **Flutter** | `flutter.py` | `from 'flutter'` imports, `extends StatelessWidget/StatefulWidget` |
| **Laravel** | `laravel.py` | File structure (`app/Http/Controllers/`), facades, `Illuminate` namespace |
| **Django** | `django.py` | `from django import`, `models.Model` inheritance |
| **FastAPI** | `django.py` (shared) | `@app.get/post/...` decorators, `from fastapi import` |
| **Express** | `express.py` | `require('express')`, `app.get/post/...` calls |
| **Rails** | `rails.py` | File structure (`app/controllers/`, `app/models/`), ActiveRecord patterns |
| **Symfony** | `symfony.py` | `use Symfony\Component`, `#[Route()]` attributes |
| **ASP.NET** | `aspnet.py` | `[ApiController]`, `: ControllerBase`, `Program.cs` patterns |
| **NestJS** | `nestjs.py` | `@Module()`, `@Controller()`, `@Injectable()` decorators |

## Output

Framework metadata is attached to parsed data before persistence:

```json
{
  "functions": [
    {
      "name": "LoginPage",
      "line_number": 10,
      "framework": "nextjs",
      "metadata": {
        "is_page": true,
        "is_api_route": false
      }
    }
  ],
  "frameworks": ["nextjs", "react"]
}
```

The `frameworks` list at the parsed-data root level is also stored in the `__file__` sentinel symbol's metadata JSON, making it queryable via `code_search`.

## Fix: Bounded Detector Cache

`_repo_detector_cache` was an unbounded dictionary that accumulated entries for every repo indexed over the lifetime of the process. Fixed by bounding to 20 entries with LRU eviction, preventing memory leaks in long-running server deployments.

## Cleanup: Dead Imports Removed

Dead framework parser imports (`nextjs_fw`, `flutter_fw`, `laravel_fw`) were removed from the framework detection module. These were unused legacy references.
