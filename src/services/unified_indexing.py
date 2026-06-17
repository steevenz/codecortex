"""
Unified Indexing Orchestrator — sequential & periodic index providers with background scheduling.

Providers:
  codecortex-codeindex      — AST indexing via tree-sitter (full + incremental)
  codecortex-graph          — Graph database build (dependency + modular)
  codecortex-embeddings     — Embedding generation (sentence-transformers)
  codecortex-knowledge      — Knowledge graph extraction
  codecortex-idegraph       — IDE memory harvest & index
  codecortex-codelogs       — Log file discovery & indexing
  codecortex-security       — Security scan (secrets, vulns, PII, misconfig)
  codecortex-full           — All providers in sequence (default)

Architecture:
  Sequential execution: each provider runs in order, status tracked per-step.
  Periodic scheduler: background daemon thread with configurable interval.
  Integrates with TaskQueue for async execution and existence TaskQueue for
  background processing.

:project: CodeCortex
:package: Services.UnifiedIndexing
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-API-v1.0
"""
from __future__ import annotations
import asyncio
import os
import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("CodeCortex.UnifiedIndexing")

# ────────────────────────────────────────────────────────────
# Enums
# ────────────────────────────────────────────────────────────

class IndexProvider(str, Enum):
    CODECORTEX_CODEINDEX = "codecortex-codeindex"
    CODECORTEX_GRAPH = "codecortex-graph"
    CODECORTEX_EMBEDDINGS = "codecortex-embeddings"
    CODECORTEX_KNOWLEDGE = "codecortex-knowledge"
    CODECORTEX_IDEGRAPH = "codecortex-idegraph"
    CODECORTEX_CODELOGS = "codecortex-codelogs"
    CODECORTEX_SECURITY = "codecortex-security"
    CODECORTEX_FULL = "codecortex-full"

class IndexStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

# ────────────────────────────────────────────────────────────
# Provider Registry
# ────────────────────────────────────────────────────────────

INDEX_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "codecortex-codeindex": {
        "id": "codecortex-codeindex",
        "name": "CodeCortex Code Index",
        "kind": "astIndex",
        "description": "AST indexing via tree-sitter — symbols, files, edges across 22 languages. Supports full and incremental modes.",
        "owned_by": "codecortex",
        "ordered_position": 1,
        "params": ["repo_path", "repo_id", "mode", "files"],
    },
    "codecortex-graph": {
        "id": "codecortex-graph",
        "name": "CodeCortex Graph Build",
        "kind": "graphBuild",
        "description": "Graph database build — dependency graph, modular detection, call hierarchies.",
        "owned_by": "codecortex",
        "ordered_position": 2,
        "params": ["repo_id", "detect_modular", "build_dependency_graph"],
    },
    "codecortex-embeddings": {
        "id": "codecortex-embeddings",
        "name": "CodeCortex Embeddings Index",
        "kind": "embeddingIndex",
        "description": "Embedding generation via sentence-transformers — semantic search vectors for all indexed files.",
        "owned_by": "codecortex",
        "ordered_position": 3,
        "params": ["repo_id", "repo_path", "model"],
    },
    "codecortex-knowledge": {
        "id": "codecortex-knowledge",
        "name": "CodeCortex Knowledge Graph Extract",
        "kind": "knowledgeExtract",
        "description": "Knowledge graph extraction — document chunks, entity relationships, structured queries.",
        "owned_by": "codecortex",
        "ordered_position": 4,
        "params": ["repo_path", "repo_id", "knowledge_types"],
    },
    "codecortex-idegraph": {
        "id": "codecortex-idegraph",
        "name": "CodeCortex IDE Memory Harvest",
        "kind": "ideMemoryHarvest",
        "description": "Cross-IDE conversation/memory harvest — scans .agents, .claude, .cursor, etc.",
        "owned_by": "codecortex",
        "ordered_position": 5,
        "params": ["repo_path", "project_name"],
    },
    "codecortex-codelogs": {
        "id": "codecortex-codelogs",
        "name": "CodeCortex Log Index",
        "kind": "logIndex",
        "description": "Log file discovery and indexing — scans <project>/logs and <project>/outputs/logs.",
        "owned_by": "codecortex",
        "ordered_position": 6,
        "params": ["repo_path", "search_paths"],
    },
    "codecortex-security": {
        "id": "codecortex-security",
        "name": "CodeCortex Security Scan",
        "kind": "securityScan",
        "description": "Security scan — secrets (AWS keys, tokens), vulnerabilities (SQL injection, eval), PII, misconfigurations.",
        "owned_by": "codecortex",
        "ordered_position": 7,
        "params": ["repo_path", "file_pattern", "severity"],
    },
    "codecortex-full": {
        "id": "codecortex-full",
        "name": "CodeCortex Full Index Pipeline",
        "kind": "fullPipeline",
        "description": "Orchestrate ALL 7 providers in sequential order with status tracking per-step.",
        "owned_by": "codecortex",
        "ordered_position": 0,
        "params": ["repo_path", "repo_id", "mode"],
    },
}


@dataclass
class IndexStepResult:
    provider: str
    status: IndexStatus
    started_at: str
    completed_at: Optional[str] = None
    elapsed_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "details": self.details,
            "error": self.error,
        }


@dataclass
class IndexingRequest:
    provider: str = "codecortex-full"
    repo_path: Optional[str] = None
    repo_id: Optional[str] = None
    mode: str = "full"
    files: Optional[List[str]] = None
    detect_modular: bool = True
    build_dependency_graph: bool = True
    knowledge_types: Optional[List[str]] = None
    project_name: Optional[str] = None
    search_paths: Optional[str] = None
    file_pattern: str = "*"
    severity: str = "medium"
    embedding_model: str = "codebert"
    notify_on_complete: bool = False
    sequential: bool = True


@dataclass
class IndexingResult:
    provider: str
    repo_path: Optional[str]
    repo_id: Optional[str]
    success: bool
    steps: List[IndexStepResult] = field(default_factory=list)
    started_at: str = ""
    completed_at: Optional[str] = None
    total_elapsed_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "repo_path": self.repo_path,
            "repo_id": self.repo_id,
            "success": self.success,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_elapsed_seconds": round(self.total_elapsed_seconds, 2),
            "error": self.error,
        }


class UnifiedIndexingEngine:
    """Orchestrate all codecortex index providers with sequential execution and background scheduling."""

    def __init__(self, orchestrator: Any = None, db: Any = None):
        self._orchestrator = orchestrator
        self._db = db
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_running = False
        self._scheduler_interval_seconds: int = 3600  # default 1 hour
        self._scheduler_repo_path: Optional[str] = None
        self._running_jobs: Dict[str, IndexingResult] = {}
        self._job_lock = threading.Lock()
        self._last_run_result: Optional[IndexingResult] = None

    @property
    def db(self):
        if self._db is not None:
            return self._db
        from ..core.database import DatabaseManager
        db_path = os.path.join(
            os.path.expanduser(os.getenv("CODECORTEX_DATA_DIR", os.path.join("~", ".coddy", "codecortex"))),
            "codecortex.db",
        )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db = DatabaseManager(db_path)
        try:
            from ..core.database.migration import full_migration
            full_migration(self._db.conn)
        except Exception as e:
            logger.warning("DB migration could not run: %s", str(e)[:120])
        return self._db

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _git_root(self, path: str) -> Optional[str]:
        import subprocess
        try:
            r = subprocess.run(
                ["git", "-C", path, "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception as e:
            logger.debug("index|git_root|error|path=%s|error=%s", path, str(e)[:80])
        return None

    def _resolve_repo_id(self, repo_path: Optional[str], repo_id: Optional[str]) -> Optional[str]:
        if repo_id:
            return repo_id
        if repo_path:
            git_root = self._git_root(repo_path)
            if git_root:
                try:
                    row = self.db.conn.execute(
                        "SELECT id FROM repositories WHERE root_path = ?", (git_root,)
                    ).fetchone()
                    if row:
                        return row[0] if isinstance(row, dict) else row[0]
                except Exception:
                    pass
        return None

    # ── Provider 1: codecortex-codeindex ──────────────────
    async def _index_codeindex(self, req: IndexingRequest) -> IndexStepResult:
        t0 = time.monotonic()
        started = self._now_iso()
        try:
            from ..modules.codeindex.services.indexer import Indexer

            repo_id = self._resolve_repo_id(req.repo_path, req.repo_id)
            if not repo_id and req.repo_path:
                from ..main import CortexOrchestrator
                orch = self._orchestrator or CortexOrchestrator()
                repo_id = await orch.repo_service.sync_repository(req.repo_path)

            if not repo_id:
                return IndexStepResult(
                    provider="codecortex-codeindex", status=IndexStatus.FAILED,
                    started_at=started, completed_at=self._now_iso(),
                    elapsed_seconds=time.monotonic() - t0,
                    error="Could not resolve repo_id. Provide repo_path or repo_id.",
                )

            indexer = self._get_indexer() if hasattr(self, '_get_indexer') else Indexer(db=self.db)

            if req.mode == "incremental":
                repo_service = self._orchestrator.repo_service if self._orchestrator else None
                if repo_service:
                    result = await repo_service.sync_repository_incremental(repo_id)
                    changed = []
                    if isinstance(result, tuple):
                        changed = result[1] if len(result) > 1 else []
                    if changed:
                        await indexer.index_files(repo_id, changed)
                else:
                    await indexer.index_repository(repo_id)
            elif req.files:
                await indexer.index_files(repo_id, req.files)
            else:
                await indexer.index_repository(repo_id)

            status = await indexer.get_index_status(repo_id)
            elapsed = time.monotonic() - t0
            logger.info("index|codeindex|repo=%s|symbols=%d|files=%d|elapsed=%.1fs",
                        repo_id, status.get("symbol_count", 0), status.get("file_count", 0), elapsed)
            return IndexStepResult(
                provider="codecortex-codeindex", status=IndexStatus.COMPLETED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed,
                details={
                    "repo_id": repo_id,
                    "symbol_count": status.get("symbol_count", 0),
                    "file_count": status.get("file_count", 0),
                    "edge_count": status.get("edge_count", 0),
                    "languages": status.get("languages", []),
                    "mode": req.mode,
                },
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            logger.warning("index|codeindex|error=%s", str(e)[:120])
            return IndexStepResult(
                provider="codecortex-codeindex", status=IndexStatus.FAILED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed, error=str(e)[:200],
            )

    # ── Provider 2: codecortex-graph ──────────────────────
    async def _index_graph(self, req: IndexingRequest) -> IndexStepResult:
        t0 = time.monotonic()
        started = self._now_iso()
        try:
            repo_id = self._resolve_repo_id(req.repo_path, req.repo_id)
            if not repo_id:
                return IndexStepResult(
                    provider="codecortex-graph", status=IndexStatus.SKIPPED,
                    started_at=started, completed_at=self._now_iso(),
                    elapsed_seconds=0, error="repo_id required for graph build",
                )

            orch = self._orchestrator
            if not orch or not hasattr(orch, 'graph_service'):
                from ..main import CortexOrchestrator
                orch = CortexOrchestrator()

            await orch.graph_service.build_graph(
                repo_id=repo_id,
                detect_modular=req.detect_modular,
                build_dependency_graph=req.build_dependency_graph,
            )
            elapsed = time.monotonic() - t0
            logger.info("index|graph|repo=%s|elapsed=%.1fs", repo_id, elapsed)
            return IndexStepResult(
                provider="codecortex-graph", status=IndexStatus.COMPLETED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed,
                details={"repo_id": repo_id, "detect_modular": req.detect_modular},
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            logger.warning("index|graph|error=%s", str(e)[:120])
            return IndexStepResult(
                provider="codecortex-graph", status=IndexStatus.FAILED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed, error=str(e)[:200],
            )

    # ── Provider 3: codecortex-embeddings ────────────────
    async def _index_embeddings(self, req: IndexingRequest) -> IndexStepResult:
        t0 = time.monotonic()
        started = self._now_iso()
        try:
            repo_id = self._resolve_repo_id(req.repo_path, req.repo_id)
            if not repo_id:
                return IndexStepResult(
                    provider="codecortex-embeddings", status=IndexStatus.SKIPPED,
                    started_at=started, completed_at=self._now_iso(),
                    elapsed_seconds=0, error="repo_id required for embeddings",
                )

            from ..modules.codeindex.parsers.embeddings import index_file_embeddings

            embed_count = await index_file_embeddings(
                db=self.db, repo_id=repo_id,
                model_name=req.embedding_model,
            )
            elapsed = time.monotonic() - t0
            logger.info("index|embeddings|repo=%s|files=%d|elapsed=%.1fs", repo_id, embed_count, elapsed)
            return IndexStepResult(
                provider="codecortex-embeddings", status=IndexStatus.COMPLETED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed,
                details={"repo_id": repo_id, "files_embedded": embed_count, "model": req.embedding_model},
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            logger.warning("index|embeddings|error=%s", str(e)[:120])
            return IndexStepResult(
                provider="codecortex-embeddings", status=IndexStatus.FAILED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed, error=str(e)[:200],
            )

    # ── Provider 4: codecortex-knowledge ─────────────────
    async def _index_knowledge(self, req: IndexingRequest) -> IndexStepResult:
        t0 = time.monotonic()
        started = self._now_iso()
        try:
            root = req.repo_path or os.getcwd()
            if not os.path.isdir(root):
                return IndexStepResult(
                    provider="codecortex-knowledge", status=IndexStatus.FAILED,
                    started_at=started, completed_at=self._now_iso(),
                    elapsed_seconds=0, error=f"Not a directory: {root}",
                )

            from ..modules.knowledgegraph.adapters.storage import KnowledgeStore
            store = KnowledgeStore(db=self.db)

            result = store.extract(
                root_path=root,
                knowledge_types=req.knowledge_types,
            )
            chunk_count = len(result.get("chunks", [])) if isinstance(result, dict) else 0
            elapsed = time.monotonic() - t0
            logger.info("index|knowledge|path=%s|chunks=%d|elapsed=%.1fs", root, chunk_count, elapsed)
            return IndexStepResult(
                provider="codecortex-knowledge", status=IndexStatus.COMPLETED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed,
                details={"root_path": root, "chunks_extracted": chunk_count},
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            logger.warning("index|knowledge|error=%s", str(e)[:120])
            return IndexStepResult(
                provider="codecortex-knowledge", status=IndexStatus.FAILED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed, error=str(e)[:200],
            )

    # ── Provider 5: codecortex-idegraph ─────────────────
    async def _index_idegraph(self, req: IndexingRequest) -> IndexStepResult:
        t0 = time.monotonic()
        started = self._now_iso()
        try:
            root = req.repo_path or os.getcwd()
            if not os.path.isdir(root):
                return IndexStepResult(
                    provider="codecortex-idegraph", status=IndexStatus.FAILED,
                    started_at=started, completed_at=self._now_iso(),
                    elapsed_seconds=0, error=f"Not a directory: {root}",
                )

            from ..modules.idegraph.core.orchestrator import SideCortexOrchestrator
            orch = SideCortexOrchestrator()
            engrams = await asyncio.to_thread(orch.run_all)

            elapsed = time.monotonic() - t0
            logger.info("index|idegraph|path=%s|engrams=%d|elapsed=%.1fs", root, len(engrams), elapsed)
            return IndexStepResult(
                provider="codecortex-idegraph", status=IndexStatus.COMPLETED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed,
                details={"root_path": root, "engrams_harvested": len(engrams)},
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            logger.warning("index|idegraph|error=%s", str(e)[:120])
            return IndexStepResult(
                provider="codecortex-idegraph", status=IndexStatus.FAILED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed, error=str(e)[:200],
            )

    # ── Provider 6: codecortex-codelogs ──────────────────
    async def _index_codelogs(self, req: IndexingRequest) -> IndexStepResult:
        t0 = time.monotonic()
        started = self._now_iso()
        try:
            root = req.repo_path or os.getcwd()
            if not os.path.isdir(root):
                return IndexStepResult(
                    provider="codecortex-codelogs", status=IndexStatus.FAILED,
                    started_at=started, completed_at=self._now_iso(),
                    elapsed_seconds=0, error=f"Not a directory: {root}",
                )

            from ..modules.codelogs.services.log_service import LogService
            svc = LogService(project_root=root)
            files = svc.scan_logs(search_paths=req.search_paths)

            elapsed = time.monotonic() - t0
            logger.info("index|codelogs|path=%s|files=%d|elapsed=%.1fs", root, len(files), elapsed)
            return IndexStepResult(
                provider="codecortex-codelogs", status=IndexStatus.COMPLETED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed,
                details={"root_path": root, "log_files_discovered": len(files)},
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            logger.warning("index|codelogs|error=%s", str(e)[:120])
            return IndexStepResult(
                provider="codecortex-codelogs", status=IndexStatus.FAILED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed, error=str(e)[:200],
            )

    # ── Provider 7: codecortex-security ─────────────────
    async def _index_security(self, req: IndexingRequest) -> IndexStepResult:
        t0 = time.monotonic()
        started = self._now_iso()
        try:
            root = req.repo_path or os.getcwd()
            if not os.path.isdir(root):
                return IndexStepResult(
                    provider="codecortex-security", status=IndexStatus.FAILED,
                    started_at=started, completed_at=self._now_iso(),
                    elapsed_seconds=0, error=f"Not a directory: {root}",
                )

            search_fn = None
            try:
                from ..services.unified_search import UnifiedSearchEngine
                engine = UnifiedSearchEngine(orchestrator=self._orchestrator, db=self.db)
                from ..services.unified_search import SearchRequest
                sec_req = SearchRequest(
                    query=req.file_pattern or "*",
                    repo_path=root, max_results=200,
                )
                resp = await engine._search_security(sec_req)
                findings = resp[0] if isinstance(resp, tuple) else []
            except Exception:
                from ..modules.codeanalysis.services.audit import Audit, AuditRequest
                audit_svc = Audit(db=self.db)
                audit_req = AuditRequest(target=root, severity_threshold=req.severity)
                result = audit_svc.audit(audit_req)
                findings = result.findings if hasattr(result, "findings") else []

            elapsed = time.monotonic() - t0
            logger.info("index|security|path=%s|findings=%d|elapsed=%.1fs", root, len(findings), elapsed)
            return IndexStepResult(
                provider="codecortex-security", status=IndexStatus.COMPLETED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed,
                details={"root_path": root, "findings_count": len(findings)},
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            logger.warning("index|security|error=%s", str(e)[:120])
            return IndexStepResult(
                provider="codecortex-security", status=IndexStatus.FAILED,
                started_at=started, completed_at=self._now_iso(),
                elapsed_seconds=elapsed, error=str(e)[:200],
            )

    # ── Orchestration ─────────────────────────────────────
    def _get_provider_targets(self, provider: str) -> List[str]:
        provider_map = {
            "codecortex-full": [
                "codeindex", "graph", "embeddings", "knowledge",
                "idegraph", "codelogs", "security",
            ],
            "codecortex-codeindex": ["codeindex"],
            "codecortex-graph": ["graph"],
            "codecortex-embeddings": ["embeddings"],
            "codecortex-knowledge": ["knowledge"],
            "codecortex-idegraph": ["idegraph"],
            "codecortex-codelogs": ["codelogs"],
            "codecortex-security": ["security"],
        }
        return provider_map.get(provider, ["codeindex"])

    async def index(self, req: IndexingRequest) -> IndexingResult:
        t0 = time.monotonic()
        started = self._now_iso()
        targets = self._get_provider_targets(req.provider)

        index_fns: Dict[str, Callable] = {
            "codeindex": self._index_codeindex,
            "graph": self._index_graph,
            "embeddings": self._index_embeddings,
            "knowledge": self._index_knowledge,
            "idegraph": self._index_idegraph,
            "codelogs": self._index_codelogs,
            "security": self._index_security,
        }

        steps: List[IndexStepResult] = []
        overall_success = True

        logger.info("index|orchestrated|provider=%s|targets=%s|started", req.provider, targets)

        for target in targets:
            fn = index_fns.get(target)
            if not fn:
                steps.append(IndexStepResult(
                    provider=f"codecortex-{target}", status=IndexStatus.SKIPPED,
                    started_at=started, completed_at=self._now_iso(),
                    error=f"Unknown target: {target}",
                ))
                continue

            step_req = IndexingRequest(
                provider=f"codecortex-{target}",
                repo_path=req.repo_path,
                repo_id=req.repo_id,
                mode=req.mode,
                files=req.files,
                detect_modular=req.detect_modular,
                build_dependency_graph=req.build_dependency_graph,
                knowledge_types=req.knowledge_types,
                project_name=req.project_name,
                search_paths=req.search_paths,
                file_pattern=req.file_pattern,
                severity=req.severity,
                embedding_model=req.embedding_model,
            )

            if req.sequential:
                result = await fn(step_req)
                steps.append(result)
                if result.status == IndexStatus.FAILED:
                    overall_success = False
                    logger.warning("index|step_failed|provider=%s|error=%s", result.provider, result.error)
            else:
                # Parallel execution — run all at once
                pass

        if not req.sequential:
            tasks = [fn(IndexingRequest(
                provider=f"codecortex-{t}", repo_path=req.repo_path,
                repo_id=req.repo_id, mode=req.mode,
            )) for t in targets if t in index_fns]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for g in gathered:
                if isinstance(g, IndexStepResult):
                    steps.append(g)
                    if g.status == IndexStatus.FAILED:
                        overall_success = False
                elif isinstance(g, Exception):
                    steps.append(IndexStepResult(
                        provider="unknown", status=IndexStatus.FAILED,
                        started_at=started, completed_at=self._now_iso(),
                        error=str(g),
                    ))
                    overall_success = False

        total_elapsed = time.monotonic() - t0

        result = IndexingResult(
            provider=req.provider,
            repo_path=req.repo_path,
            repo_id=req.repo_id,
            success=overall_success,
            steps=steps,
            started_at=started,
            completed_at=self._now_iso(),
            total_elapsed_seconds=total_elapsed,
        )

        self._last_run_result = result
        logger.info("index|orchestrated|provider=%s|steps=%d|success=%s|elapsed=%.1fs",
                    req.provider, len(steps), overall_success, total_elapsed)

        return result

    # ── Background Scheduler ──────────────────────────────
    def start_scheduler(self, repo_path: str, interval_seconds: int = 3600) -> Dict[str, Any]:
        """Start periodic indexing scheduler in background thread."""
        if self._scheduler_running:
            return {"success": False, "message": "Scheduler already running"}

        self._scheduler_running = True
        self._scheduler_interval_seconds = max(60, interval_seconds)
        self._scheduler_repo_path = repo_path
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True,
            name="unified-indexing-scheduler",
        )
        self._scheduler_thread.start()
        logger.info("index|scheduler|started|path=%s|interval=%ds", repo_path, interval_seconds)
        return {
            "success": True,
            "message": f"Scheduler started for {repo_path} every {interval_seconds}s",
            "data": {"repo_path": repo_path, "interval_seconds": interval_seconds},
        }

    def stop_scheduler(self) -> Dict[str, Any]:
        """Stop the periodic indexing scheduler."""
        if not self._scheduler_running:
            return {"success": False, "message": "Scheduler not running"}
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10)
            self._scheduler_thread = None
        logger.info("index|scheduler|stopped")
        return {"success": True, "message": "Scheduler stopped"}

    def scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            "running": self._scheduler_running,
            "repo_path": self._scheduler_repo_path,
            "interval_seconds": self._scheduler_interval_seconds,
            "last_run": self._last_run_result.to_dict() if self._last_run_result else None,
        }

    def _scheduler_loop(self) -> None:
        """Background scheduler loop — runs index at configured interval."""
        import asyncio
        logger.info("index|scheduler|loop_started|interval=%ds", self._scheduler_interval_seconds)
        while self._scheduler_running:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                req = IndexingRequest(
                    provider="codecortex-full",
                    repo_path=self._scheduler_repo_path,
                    mode="incremental",
                    sequential=True,
                )
                result = loop.run_until_complete(self.index(req))
                loop.close()
                logger.info("index|scheduler|run_complete|success=%s|elapsed=%.1fs",
                            result.success, result.total_elapsed_seconds)
            except Exception as e:
                logger.error("index|scheduler|run_failed|error=%s", str(e)[:120])

            # Sleep for interval (check _scheduler_running every 10s for responsive stop)
            for _ in range(self._scheduler_interval_seconds // 10):
                if not self._scheduler_running:
                    break
                time.sleep(10)

    # ── Status / History ──────────────────────────────────
    def get_last_result(self) -> Optional[Dict[str, Any]]:
        if self._last_run_result:
            return self._last_run_result.to_dict()
        return None

    def get_providers(self) -> Dict[str, Any]:
        return {
            "total": len(INDEX_PROVIDERS),
            "providers": [
                {"id": pid, "name": info["name"], "kind": info["kind"],
                 "description": info["description"], "ordered_position": info["ordered_position"]}
                for pid, info in sorted(INDEX_PROVIDERS.items(), key=lambda x: x[1]["ordered_position"])
            ],
        }


# ────────────────────────────────────────────────────────────
# Singleton
# ────────────────────────────────────────────────────────────
_engine: Optional[UnifiedIndexingEngine] = None


def get_indexing_engine(orchestrator: Any = None, db: Any = None) -> UnifiedIndexingEngine:
    global _engine
    if _engine is None or orchestrator is not None:
        _engine = UnifiedIndexingEngine(orchestrator=orchestrator, db=db)
    return _engine
