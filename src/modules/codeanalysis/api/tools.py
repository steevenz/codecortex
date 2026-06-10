"""
Module tools – Single Responsibility: Register and handle MCP tools for code analysis domain.
4 tools: code_analyze, code_search, code_audit, code_status
Removed: code_refactor (handled by coderefactor domain).

:project: CodeCortex
:package: Modules.Codeanalysis.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""
from __future__ import annotations

from typing import Optional, Dict, Any, Callable, List
from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id, get_db_path
from src.modules.codeanalysis.core.dtos import (
    AnalyzeRequest, SearchRequest, AuditRequest, StatusRequest,
)

def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register 4 consolidated code analysis tools with ~/.aicoders/ API standard compliance.
    """

    @mcp.tool()
    async def code_analyze(
        target: str,
        targets: Optional[List[str]] = None,  # Batch: multiple targets
        mode: str = "auto",
        summary: Optional[bool] = None,
        max_depth: int = 3,
        focus: Optional[str] = None,
        follow_depth: int = 1,
        cursor: Optional[str] = None,
        page_size: int = 100,
        include_docstring: bool = True,
        include_comments: bool = False,
        repo_id: Optional[str] = None,
        parallel: bool = True,
        max_workers: int = 4,
    ) -> Dict[str, Any]:
        """
        Analyze code structure with Tree-Sitter AST extraction and knowledge graph.
        Supports batch analysis of multiple targets with parallel processing.

        @param target: Path file atau direktori (wajib).
        @param targets: List multiple paths untuk batch analysis (optional).
        @param mode: "overview" | "detailed" | "symbol_focus" | "auto" | "batch_detailed".
        @param summary: Hasilkan ringkasan kompak jika output > 50K chars.
        @param max_depth: Kedalaman tree untuk mode overview (max 10).
        @param focus: Nama simbol untuk mode symbol_focus (case-sensitive).
        @param follow_depth: Kedalaman call graph (max 3).
        @param cursor: Token pagination dari response sebelumnya.
        @param page_size: Jumlah item per halaman (max 500).
        @param include_docstring: Sertakan docstring.
        @param include_comments: Sertakan baris komentar.
        @param repo_id: Repository UUID untuk path resolution.
        @param parallel: Enable parallel processing untuk batch analysis (default: true).
        @param max_workers: Thread pool size untuk parallel processing (default: 4).
        @return: Analysis results with graph structure and metrics.
        """
        from src.modules.codeanalysis.services.analyze import Analyze
        orchestrator = orchestrator_factory()

        if not target:
            return api_response(success=False, status_code=400,
                                message="target is required for analysis",
                                data=None, request_id=new_request_id(),
                                error_code="CA_001")

        service = Analyze(db=orchestrator.db, fs_service=orchestrator.fs_service)
        request = AnalyzeRequest(
            target=target, targets=targets, mode=mode, summary=summary,
            max_depth=min(max_depth, 10), focus=focus,
            follow_depth=min(follow_depth, 3), cursor=cursor,
            page_size=min(page_size, 500),
            include_docstring=include_docstring,
            include_comments=include_comments, repo_id=repo_id,
            parallel=parallel, max_workers=max_workers,
        )

        try:
            result = service.analyze(request)
            data = {
                "mode": result.mode,
                "target": result.target,
                "count": result.count,
                "symbols": [
                    {"name": s.name, "kind": s.kind, "file": s.file_path,
                     "line_start": s.line_start, "line_end": s.line_end,
                     "signature": s.signature, "docstring": s.docstring,
                     "parent_symbol": s.parent_symbol,
                     "calls": s.calls,
                     "referenced_by": s.referenced_by}
                    for s in result.symbols
                ],
                "edges": [
                    {"from": e.from_symbol, "to": e.to_symbol,
                     "relation": e.relation, "weight": e.weight}
                    for e in result.edges
                ],
                "tree": result.tree,
            }
            return api_response(success=True, insight="code_analyze", status_code=200,
                                message="Code analysis completed",
                                data=data, request_id=new_request_id(),
                                summary_mode=bool(summary),
                                pagination={
                                    "next_cursor": result.next_cursor,
                                    "has_more": result.has_more,
                                    "total": result.count,
                                    "limit": min(page_size, 500),
                                })
        except (FileNotFoundError, ValueError) as e:
            return api_response(success=False, status_code=404,
                                message=str(e), data=None,
                                request_id=new_request_id(), error_code="CA_002")
        except Exception as e:
            return api_response(success=False, status_code=500,
                                message=f"Analysis error: {e}", data=None,
                                request_id=new_request_id(), error_code="CA_500")

    @mcp.tool()
    async def code_search(
        query: str,
        search_type: str = "multi",
        repo_id: Optional[str] = None,
        limit: int = 50,
        file_pattern: str = "*",
        include_content: bool = False,
        semantic: bool = False,
        graph: bool = False,
        graph_relations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Multi-layer code search: FTS text (always) + optional semantic + graph enrichment.

        Layer 1 - Text search (always): FTS5 on symbol names and signatures.
        Layer 2 - Semantic (semantic=True): embedding similarity for related concepts.
        Layer 3 - Graph (graph=True): relationships (calls, inherits, imports) per match.

        Results cached for 5 minutes. Includes synced_at metadata.

        @param query: Search query string (required).
        @param search_type: "multi" | "symbol" | "regex" | "graph" | "semantic" (default: "multi").
        @param repo_id: Repository UUID for scope.
        @param limit: Max results per layer (default 50, max 200).
        @param file_pattern: Glob filter for files (default: "*").
        @param include_content: Include code snippets in results (default: false).
        @param semantic: Enable semantic embedding enrichment.
        @param graph: Enable graph relationship enrichment.
        @param graph_relations: Relation types to include (default: calls, inherits, imports).
        @return: Multi-layer search results with matches, semantic hits, relationships, and metadata.
        """
        from src.modules.codeanalysis.services.search import Search
        orchestrator = orchestrator_factory()

        if not query:
            return api_response(success=False, status_code=400,
                                message="query is required",
                                data=None, request_id=new_request_id(),
                                error_code="CA_010")

        service = Search(db=orchestrator.db)
        request = SearchRequest(
            query=query, repo_id=repo_id, search_type=search_type,
            limit=min(limit, 200), cursor=None,
            file_pattern=file_pattern, include_content=include_content,
        )

        try:
            result = service.search(request, semantic=semantic, graph=graph, graph_relations=graph_relations)
            return api_response(success=True, insight="code_search", status_code=200,
                                message=f"Found {result.get('total_matches', 0)} matches" +
                                (f" + {result.get('total_semantic', 0)} semantic" if semantic else "") +
                                (f" + {result.get('total_relationships', 0)} relationships" if graph else ""),
                                data=result, request_id=new_request_id())
        except ValueError as e:
            return api_response(success=False, status_code=400, message=str(e),
                                data=None, request_id=new_request_id(), error_code="CA_011")
        except Exception as e:
            return api_response(success=False, status_code=500,
                                message=f"Search error: {e}", data=None,
                                request_id=new_request_id(), error_code="CA_500")

    @mcp.tool()
    async def code_audit(
        target: str,
        scan_categories: Optional[List[str]] = None,
        severity_threshold: str = "medium",
        entropy_threshold: float = 4.5,
        include_comments: bool = False,
        max_file_size_kb: int = 1024,
        files: Optional[List[str]] = None,
        output_format: str = "json",
        use_ast: bool = True,
        use_aiignore: bool = True,
        repository_id: Optional[str] = None,
        since: Optional[str] = None,
        enable_auto_fix: bool = False,  # Generate auto-fix suggestions
        apply_auto_fix: bool = False,    # Apply fixes (requires dry_run=False)
        dry_run: bool = True,            # Safety: don't modify files when True
    ) -> Dict[str, Any]:
        """
        Audit source code for ~/.aicoders/ standards compliance.
        Scans 24+ categories: security + coding standards + architecture + syntax + API compliance.
        Outputs compliance_score (0-100) + actionable findings with error codes + remediation.

        @param target: Path file atau direktori (wajib).
        @param scan_categories: ["secrets","pii","misconfig","vulns","comments",
                               "naming","type_hints","file_structure","class_docblock",
                               "modular","modular_structure","architecture","syntax",
                               "error_handling","di_compliance","docblock","logging",
                               "api_response","semver","pwa","crossplatform",
                               "test_debug","codification","coding_naming"]
        @param severity_threshold: "low" | "medium" | "high" | "critical".
        @param entropy_threshold: Ambang entropy untuk secrets detection.
        @param include_comments: Sertakan komentar untuk tag detection.
        @param max_file_size_kb: Max file size (max 5000).
        @param files: Daftar file spesifik.
        @param output_format: "json" | "csv" | "report".
        @param use_ast: Gunakan cached AST untuk akurasi lebih tinggi.
        @param use_aiignore: Baca .aiignore untuk exclude patterns.
        @param repository_id: Repository UUID untuk persist findings.
        @param since: ISO 8601 timestamp untuk incremental scan (only files modified since).
        @param enable_auto_fix: Generate auto-fix code suggestions (default: false).
        @param apply_auto_fix: Apply auto-fixes to files (DANGEROUS, requires dry_run=false).
        @param dry_run: Safety mode - don't modify files even when apply_auto_fix=true.
        @return: Audit findings + compliance_score + auto-fix suggestions + recommendations.
        """
        from src.modules.codeanalysis.services.audit import Audit
        orchestrator = orchestrator_factory()

        if not target:
            return api_response(success=False, status_code=400,
                                message="target is required for audit",
                                data=None, request_id=new_request_id(),
                                error_code="CA_020")

        service = Audit(db=orchestrator.db, fs_service=orchestrator.fs_service)
        request = AuditRequest(
            target=target, scan_categories=scan_categories,
            severity_threshold=severity_threshold,
            entropy_threshold=entropy_threshold,
            include_comments=include_comments,
            max_file_size_kb=min(max_file_size_kb, 5000),
            files=files, output_format=output_format,
            use_ast=use_ast, use_aiignore=use_aiignore,
            repository_id=repository_id, since=since,
            enable_auto_fix=enable_auto_fix,
            apply_auto_fix=apply_auto_fix,
            dry_run=dry_run,
        )

        try:
            result = service.audit(request)
            data = {
                "target": result.target,
                "scan_categories": result.scan_categories,
                "scanned_files": result.scanned_files,
                "compliance_score": result.compliance_score,
                "summary": result.summary,
                "findings": [
                    {"category": f.category, "severity": f.severity,
                     "file": f.file, "line": f.line, "column": f.column,
                     "code": f.code, "message": f.message,
                     "details": f.details,
                     "context": f.context, "confidence": f.confidence,
                     "remediation": f.remediation,
                     "standard_ref": f.standard_ref,
                     "auto_fix_available": f.auto_fix_available,
                     "auto_fix_code": f.auto_fix_code,
                     "auto_fix_description": f.auto_fix_description,
                     "fix_applied": f.fix_applied,
                     "fix_diff": f.fix_diff}
                    for f in result.findings
                ],
                "recommendations": result.recommendations,
                "errors": result.errors,
            }
            # Mark audit as synced
            if repository_id:
                try:
                    from src.core.database.integrity import FileIntegrity
                    FileIntegrity(orchestrator.db).mark_synced(repository_id, "audit")
                except Exception:
                    pass
            return api_response(success=True, insight="code_audit", status_code=200,
                                message=f"Code audit complete: {len(result.findings)} findings in {result.scanned_files} files. Score: {result.compliance_score}/100",
                                data=data, request_id=new_request_id())
        except FileNotFoundError as e:
            return api_response(success=False, status_code=404,
                                message=str(e), data=None,
                                request_id=new_request_id(), error_code="CA_021")
        except Exception as e:
            return api_response(success=False, status_code=500,
                                message=f"Audit error: {e}", data=None,
                                request_id=new_request_id(), error_code="CA_500")

    @mcp.tool()
    async def code_status(
        path: str,
        repo_id: Optional[str] = None,
        include_metrics: bool = True,
        include_vcs: bool = True,
        include_symbols: bool = True,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get code metrics, VCS status, and symbol statistics for a repository.

        @param path: Repository path (wajib).
        @param repo_id: Repository UUID untuk path resolution.
        @param include_metrics: Include LOC, comment ratio, language breakdown.
        @param include_vcs: Include git/svn status.
        @param include_symbols: Include symbol counts by kind.
        @param language: Filter metrics by language.
        @return: Status with metrics, VCS info, and symbol stats.
        """
        from src.modules.codeanalysis.services.status import Status
        orchestrator = orchestrator_factory()

        if not path:
            return api_response(success=False, status_code=400,
                                message="path is required for status",
                                data=None, request_id=new_request_id(),
                                error_code="CA_030")

        service = Status(db=orchestrator.db)
        request = StatusRequest(
            path=path, repo_id=repo_id,
            include_metrics=include_metrics,
            include_vcs=include_vcs,
            include_symbols=include_symbols,
            language=language,
        )

        # Try cached stats first (instant)
        if repo_id and include_metrics:
            try:
                from src.core.database.index_cache import IndexCache
                stats = IndexCache(orchestrator.db).get_stats(repo_id)
                if stats:
                    from src.core.database.integrity import FileIntegrity
                    state = FileIntegrity(orchestrator.db).get_sync_state(repo_id)
                    return api_response(success=True, insight="code_status", status_code=200,
                        message=f"Status retrieved from cache",
                        data={
                            "target": path, "repo_id": repo_id,
                            "index_stats": stats,
                            "synced_at": stats.get("synced_at"),
                            "sync_state": {k: v for k, v in state.items() if k.endswith("_synced_at")},
                            "cached": True,
                        }, request_id=new_request_id())
            except Exception:
                pass

        try:
            result = service.get_status(request)
            data = {
                "target": result.target,
                "repo_id": result.repo_id,
                "summary": {
                    "files": result.summary.files if result.summary else 0,
                    "directories": result.summary.directories if result.summary else 0,
                    "total_lines": result.summary.total_lines if result.summary else 0,
                    "code_lines": result.summary.code_lines if result.summary else 0,
                    "comment_lines": result.summary.comment_lines if result.summary else 0,
                    "blank_lines": result.summary.blank_lines if result.summary else 0,
                    "comment_ratio": result.summary.comment_ratio if result.summary else 0.0,
                    "languages": result.summary.languages if result.summary else {},
                } if result.summary else None,
                "symbols": result.symbols,
                "graph_stats": {
                    "nodes": result.graph_stats.nodes if result.graph_stats else 0,
                    "edges": result.graph_stats.edges if result.graph_stats else 0,
                    "density": result.graph_stats.density if result.graph_stats else 0.0,
                    "components": result.graph_stats.components if result.graph_stats else 0,
                } if result.graph_stats else None,
                "vcs": {
                    "type": result.vcs.type if result.vcs else "none",
                    "branch": result.vcs.branch if result.vcs else None,
                    "commit": result.vcs.commit if result.vcs else None,
                    "last_commit_date": result.vcs.last_commit_date if result.vcs else None,
                    "uncommitted_changes": result.vcs.uncommitted_changes if result.vcs else 0,
                    "untracked_files": result.vcs.untracked_files if result.vcs else 0,
                } if result.vcs else None,
            }
            return api_response(success=True, insight="code_status", status_code=200,
                                message="Status retrieved",
                                data=data, request_id=new_request_id())
        except FileNotFoundError as e:
            return api_response(success=False, status_code=404,
                                message=str(e), data=None,
                                request_id=new_request_id(), error_code="CA_031")
        except Exception as e:
            return api_response(success=False, status_code=500,
                                message=f"Status error: {e}", data=None,
                                request_id=new_request_id(), error_code="CA_500")
