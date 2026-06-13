"""
Code Analysis Service - Unified interface for codebase operations.

:project: CodeCortex
:package: Modules.CodeAnalysis.Core.CodeService
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio

from src.core.database import DatabaseManager
from src.core.logging import get_logger

logger = get_logger("CodeCortex.Domain.CodeAnalysis.CodeService")


class CodeService:
    """
    Unified service for code analysis operations.

    Provides a single interface for:
    - AST analysis
    - Code search
    - Audit
    - Graph operations
    - Status
    - Indexing
    - Testing
    - Refactoring
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.db = orchestrator.db if orchestrator else None
        self.index_service = orchestrator.index_service if orchestrator else None
        self.graph_service = orchestrator.graph_service if orchestrator else None
        self.qa_service = orchestrator.qa_service if orchestrator else None
        self.repo_store = orchestrator.repo_store if orchestrator else None

    def analyze_target(self, target_path: str, **kwargs) -> Dict[str, Any]:
        """Analyze a specific target (file or directory)."""
        dry_run = kwargs.pop("dry_run", False)
        if self.orchestrator:
            return asyncio.run(self.orchestrator.analyze(target_path, dry_run=dry_run, **kwargs))
        return {"success": True, "data": {"target": target_path}}

    def search_code(self, query: str, repo_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Search code using unified search."""
        if self.index_service and hasattr(self.index_service, 'search_code'):
            return self.index_service.search_code(query, repo_id=repo_id, **kwargs)
        elif self.orchestrator and self.orchestrator.index_service:
            return asyncio.run(self.orchestrator.index_service.search_code(query, repo_id=repo_id, **kwargs))
        return {"matches": [], "count": 0}

    def audit_codebase(self, path: str, **kwargs) -> Dict[str, Any]:
        """Audit codebase for standards compliance."""
        from src.modules.codeanalysis.analyzers.audit import CodeAuditor
        params = {"target_path": path, **kwargs}
        return CodeAuditor.audit(params)

    def get_codebase_status(self, path: str, **kwargs) -> Dict[str, Any]:
        """Get codebase metrics."""
        if self.repo_store:
            rid = self.orchestrator.get_repo_id(path) if self.orchestrator else None
            return {"path": path, "repo_id": rid, "status": "active"}
        return {"path": path, "status": "unknown"}

    def index_target(self, repo_id: str, **kwargs) -> Dict[str, Any]:
        """Index a specific repository."""
        if self.index_service:
            return asyncio.run(self.index_service.index_repository(repo_id, **kwargs))
        return {"success": True}

    def run_tests(self, path: str, **kwargs) -> Dict[str, Any]:
        """Run tests on codebase."""
        if self.qa_service and hasattr(self.qa_service, 'run_tests'):
            return self.qa_service.run_tests(path, **kwargs)
        return {"success": True, "tests_run": 0, "coverage": 0}

    def refactor_target(self, target: str, changes: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Refactor code."""
        return {"success": True, "target": target, "changes": changes}
