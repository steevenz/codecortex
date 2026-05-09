# Phase 4: Advanced Code Intelligence Features

**Source:** GitNexus pipeline phases (framework-detection.ts, routes.ts, orm.ts, worker-pool)  
**Total Features:** 4 | **Total Effort:** ~12h

---

## Step 11: Framework Detection (~3h)
**Domain:** CodeIndex | **Effort:** Medium | **Impact:** High

Detect frameworks from project files (package.json, requirements.txt, composer.json) and source patterns.
- Python: Django (urls.py, views.py), FastAPI (routers/), Flask (app.py, routes.py)
- TypeScript: Next.js (pages/, app/), Express (routes/), NestJS (modules/)
- Pattern detection from imports and decorators

## Step 12: Route Extraction (~4h)
**Domain:** CodeGraph | **Effort:** Medium | **Impact:** High

Extract API endpoints and navigation routes from framework patterns.
- FastAPI: `@app.get("/api/users")` → /api/users [GET]
- Django: `path("users/", views.list)` → /users/ [GET]
- Next.js: `pages/users/[id].tsx` → /users/:id
- Express: `router.get("/users", handler)` → /users [GET]
- Store as Route nodes + HANDLES_ROUTE edges in KnowledgeGraph

## Step 13: ORM Dataflow Analysis (~3h)
**Domain:** CodeGraph | **Effort:** Medium | **Impact:** Medium

Extract model-database relationships from ORM definitions.
- SQLAlchemy: `class User(Base)` → model "User" with table "users"
- Django: `class User(models.Model)` → model "User"
- Prisma: `model User { ... }` → model "User"
- Store model info + QUERIES edges between code and data

## Step 14: Worker Pool for Parallel Parsing (~2h)
**Domain:** CodeIndex | **Effort:** Low | **Impact:** Medium

Parse files in parallel using a configurable worker pool.
- ThreadPoolExecutor with configurable max_workers (default: CPU count)
- Threshold: parallel if files > 15 OR total bytes > 512KB
- Chunked processing for memory efficiency
- Same pattern as GitNexus's worker-pool.ts

---

## Order
```
Step 11 → Step 14 → Step 12 → Step 13
(Framework Detection → Worker Pool → Route Extraction → ORM Dataflow)
```
