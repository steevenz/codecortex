"""
ActionRouter — Maps top-level MCP tool actions to underlying domain service calls.

4 tools → 39 actions → 38 domain tools via lazy import dispatch.

:project: CodeCortex
:package: Api.Orchestration
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-API-v1.0
"""
from __future__ import annotations
import time
import logging
from typing import Any, Callable, Dict, List, Optional

from ..core import api_response, new_request_id

logger = logging.getLogger("CodeCortex.API.Router")

# ────────────────────────────────────────────────────────────
# Action → module resolution map
# ────────────────────────────────────────────────────────────
REPO_ACTIONS = {
    "init", "inspect", "analyze", "sync", "audit", "staleness",
    "list", "compact", "cleanup", "dump", "restore", "git", "svn",
}
FS_ACTIONS = {
    "read", "write", "delete", "copy", "move", "mkdir", "list",
    "search", "watch", "usage", "audit", "read_lines", "write_lines",
}
CODEBASE_ACTIONS = {
    "analyze", "search", "audit", "graph", "status", "index", "test", "refactor",
}
SCAFFOLDER_ACTIONS = {
    "list_stacks", "get_stack", "validate_name", "list_licenses",
    "generate_content", "generate_class", "create_project",
}
UPDATE_ACTIONS = {
    "check", "status", "download", "apply", "signal", "dismiss",
}

class ActionRouter:
    """Routes action→domain→tool function with lazy import and uniform response."""

    def __init__(self, orchestrator_factory: Callable[[], Any]):
        self._factory = orchestrator_factory
        self._orch = None

    @property
    def orchestrator(self):
        if self._orch is None:
            self._orch = self._factory()
        return self._orch

    def _ok(self, message: str, data: Any, meta: Optional[Dict] = None,
            request_id: Optional[str] = None, insight: Any = None,
            duration_ms: Optional[int] = None) -> Dict[str, Any]:
        result = api_response(success=True, status_code=200, message=message,
                              data=data, request_id=request_id or new_request_id(),
                              insight=insight, duration_ms=duration_ms)
        if meta:
            result.setdefault("meta", {}).update(meta)
        return result

    def _err(self, message: str, error_code: str, request_id: Optional[str] = None,
             status_code: int = 400) -> Dict[str, Any]:
        return api_response(success=False, status_code=status_code, message=message,
                            data=None, request_id=request_id or new_request_id(),
                            error_code=error_code)

    def _fs_error(self, message: str, error_code: str, status_code: int = 400,
                  recommendations: Optional[List[str]] = None,
                  context: Optional[Dict[str, Any]] = None,
                  request_id: Optional[str] = None) -> Dict[str, Any]:
        """Structured filesystem error with diagnostic context and AI coder recommendations.

        Returns a consistent JSON error response that helps AI coders diagnose
        and resolve filesystem operation failures.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error code (e.g., API_404, API_403).
            status_code: HTTP-style status code.
            recommendations: List of actionable steps for the AI coder.
            context: Dict with additional diagnostic info (path, resolved, etc.).
            request_id: Optional request identifier.
        """
        result = api_response(
            success=False,
            status_code=status_code,
            message=message,
            data=None,
            request_id=request_id or new_request_id(),
            error_code=error_code,
            details={
                "recommendations": recommendations or [],
                "context": context or {},
            },
        )
        return result

    def _resolve_id(self, repo_id: Optional[str], repo_path: Optional[str]) -> Optional[str]:
        if repo_id:
            return repo_id
        if repo_path:
            import os
            from pathlib import Path
            resolved = str(Path(repo_path).resolve())
            if self._orch:
                return self.orchestrator.get_repo_id(resolved)
        return None

    async def dispatch(self, tool: str, action: str, args: Dict) -> Dict:
        """Unified dispatch method for all tools."""
        tool_lower = tool.lower()
        action_lower = action.lower()

        if tool_lower == "codecortex_repository":
            return await self.dispatch_repository(action, args.get("repo_path"), args.get("repo_id"), args)
        elif tool_lower == "codecortex_filesystem":
            return await self.dispatch_filesystem(action, args.get("path"), args.get("repo_id"), args)
        elif tool_lower == "codecortex_codebase":
            return await self.dispatch_codebase(action, args.get("repo_id"), args.get("repo_path"), args)
        elif tool_lower == "codecortex_scaffolder":
            return await self.dispatch_scaffolder(action, args)
        else:
            return self._err(f"Unknown tool: {tool}", "API_400")

    async def dispatch_repository(self, action: str, repo_path: Optional[str],
                            repo_id: Optional[str], args: Dict) -> Dict:
        action_lower = action.lower()
        if action_lower == "init": return await self._repo_init(repo_path, args)
        elif action_lower == "inspect": return await self._repo_inspect(repo_path, repo_id, args)
        elif action_lower == "analyze": return await self._repo_analyze(repo_path, repo_id, args)
        elif action_lower == "sync": return await self._repo_sync(repo_path, repo_id, args)
        elif action_lower == "audit": return await self._repo_audit(repo_path, repo_id, args)
        elif action_lower == "staleness": return await self._repo_staleness(repo_path, repo_id, args)
        elif action_lower == "list": return await self._repo_list(args)
        elif action_lower == "compact": return await self._repo_compact(repo_path, repo_id, args)
        elif action_lower == "cleanup": return await self._repo_cleanup(repo_path, repo_id, args)
        elif action_lower == "dump": return await self._repo_dump(repo_path, repo_id, args)
        elif action_lower == "restore": return await self._repo_restore(args)
        elif action_lower == "git": return await self._repo_git(repo_path, args)
        elif action_lower == "svn": return await self._repo_svn(args)
        else: return self._err(f"Unknown repository action: {action}", "API_400")

    # ── (Removed duplicate dispatch_filesystem) ──

    async def _repo_init(self, repo_path: str, args: Dict) -> Dict:
        import os
        from pathlib import Path
        from ..core.database import cleanup_project
        from ..modules.codeanalysis.analyzers.audit import CodeAuditor
        from ..modules.coderepository.core.utils import extract_vcs_metadata

        if not repo_path:
            return self._err("repo_path required for init", "API_400")
        resolved = str(Path(repo_path).resolve())
        remote_url = args.get("remote_url")
        force = args.get("force", False)
        run_audit = args.get("run_audit", True)
        audit_categories = args.get("audit_categories")
        max_depth = args.get("max_depth")
        request_id = new_request_id()

        try:
            existing_id = self.orchestrator.get_repo_id(resolved)
            if existing_id:
                if not force:
                    return self._ok("Repository already initialized", {"repo_id": existing_id},
                                    request_id=request_id)
                cleanup_project(self.orchestrator.db.conn, existing_id)

            repo_id = await self.orchestrator.repo_service.initialize(
                resolved, max_depth=max_depth, remote_url=remote_url,
            )
            tree = self.orchestrator.fs_service.get_codebase_tree(path=resolved)

            audit_result = None
            if run_audit:
                auditor = CodeAuditor(db=self.orchestrator.db)
                audit_result = auditor.audit({
                    "target": resolved, "scan_categories": audit_categories,
                    "output_format": "json",
                })

            vcs_meta = extract_vcs_metadata(resolved)
            if vcs_meta:
                self.orchestrator.repo_store.update_vcs_metadata(repo_id, vcs_meta)

            return self._ok("Repository initialized", {
                "repo_id": repo_id, "tree": tree, "audit": audit_result,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Init failed: {e}", "API_500", status_code=500)

    async def _repo_inspect(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        import os
        import subprocess
        from pathlib import Path
        from datetime import datetime, timezone

        rp = repo_path
        if not rp:
            return self._err("repo_path required for inspect", "API_400")
        resolved = str(Path(rp).resolve())
        request_id = new_request_id()
        diag = args.get("include_git_diagnostics", True)
        include_index = args.get("include_index_metadata", True)
        include_vcs = args.get("include_vcs_status", True)
        include_files = args.get("include_file_stats", True)
        include_deps = args.get("include_dependency_summary", False)
        period = args.get("diagnostic_period", "1_year")
        timeout = args.get("timeout", 30)
        rid = repo_id or self.orchestrator.get_repo_id(resolved)

        data = {"target": resolved, "repo_id": rid, "exists": os.path.exists(resolved)}

        try:
            if diag and os.path.exists(os.path.join(resolved, ".git")):
                data["git"] = self._run_git_diagnostics(resolved, period, timeout)
        except Exception:
            pass
        try:
            if include_files:
                nfiles = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM files WHERE repository_id=? AND deleted_at IS NULL",
                    (rid,)
                ).fetchone()[0] if rid else 0
                nsym = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM symbols WHERE repository_id=?",
                    (rid,)
                ).fetchone()[0] if rid else 0
                data["stats"] = {"files": nfiles, "symbols": nsym}
        except Exception:
            pass
        try:
            if include_deps and rid:
                deps = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM edges WHERE repository_id=?",
                    (rid,)
                ).fetchone()[0] if rid else 0
                data["dependencies"] = deps
        except Exception:
            pass

        return self._ok("Inspection complete", data, request_id=request_id)

    async def _repo_analyze(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        if not repo_path:
            return self._err("repo_path required for analyze", "API_400")
        from pathlib import Path
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        force = args.get("force", False)
        incremental = args.get("incremental", True)
        build_graph = args.get("build_graph", True)
        extract_symbols = args.get("extract_symbols", True)
        store_embeddings = args.get("store_embeddings", False)
        embedding_model = args.get("embedding_model", "codebert")
        timeout = args.get("timeout", 300)
        dry_run = args.get("dry_run", False)

        try:
            result = await self.orchestrator.analyze(
                resolved, request_id=request_id, dry_run=dry_run,
                max_depth=None, include_codemap=True,
            )
            if store_embeddings and result.get("repository_id"):
                rid = result["repository_id"]
                await self.orchestrator.index_service.generate_embeddings(
                    rid, model=embedding_model, request_id=request_id,
                )
            return self._ok("Analysis complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Analysis failed: {e}", "API_500", status_code=500)

    async def _repo_sync(self, repo_path: Optional[str], repo_id: Optional[str],
                         args: Dict) -> Dict:
        import os
        from pathlib import Path
        if not repo_path:
            return self._err("repo_path required for sync", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        mode = args.get("mode", "auto")
        scope = args.get("scope", {})
        reindex = args.get("reindex_updated", True)
        remove_deleted = args.get("remove_deleted", True)
        dry_run = args.get("dry_run", False)

        try:
            repo = self.orchestrator.repo_store.get_repository_by_path(resolved)
            if not repo:
                return self._err(f"Repository not found at {resolved}", "API_404", status_code=404)
            rid = repo.get("id") or repo_id
            if dry_run:
                changed = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM files WHERE repository_id=? AND updated_at > COALESCE(indexed_at, '1970-01-01')",
                    (rid,)
                ).fetchone()[0] if rid else 0
                return self._ok("Dry run — would sync", {"changed_files": changed, "repo_id": rid},
                                request_id=request_id)
            if mode in ("full", "auto"):
                rid = await self.orchestrator.repo_service.sync_repository(
                    resolved, request_id=request_id,
                )
                await self.orchestrator.index_service.index_repository(
                    rid, request_id=request_id,
                )
            elif mode == "incremental":
                inc_result = await self.orchestrator.repo_service.sync_repository_incremental(rid)
                rid = inc_result[0] if isinstance(inc_result, tuple) else inc_result
            return self._ok("Sync complete", {"repo_id": rid, "mode": mode},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"Sync failed: {e}", "API_500", status_code=500)

    async def _repo_audit(self, repo_path: Optional[str], repo_id: Optional[str],
                          args: Dict) -> Dict:
        import os, re, json
        from pathlib import Path
        if not repo_path:
            return self._err("repo_path required for audit", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        secrets = args.get("secrets", True)
        scan_cats = args.get("scan_categories")

        try:
            findings = []
            if secrets and os.path.exists(resolved):
                from ..modules.coderepository.core.utils import scan_secrets
                findings = scan_secrets(resolved,
                    exclude_paths=args.get("scope", {}).get("exclude"),
                )
            return self._ok("Audit complete", {
                "target": resolved, "findings": findings,
                "count": len(findings) if isinstance(findings, list) else 0,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Audit failed: {e}", "API_500", status_code=500)

    async def _repo_staleness(self, repo_path: Optional[str], repo_id: Optional[str],
                              args: Dict) -> Dict:
        from pathlib import Path
        if not repo_path:
            return self._err("repo_path required for staleness", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()

        try:
            repo = self.orchestrator.repo_store.get_repository_by_path(resolved)
            if not repo:
                return self._err("Repository not found", "API_404", status_code=404)
            rid = repo.get("id")
            last_sync = repo.get("sync_at")
            return self._ok("Staleness check", {
                "repo_id": rid, "sync_at": last_sync, "is_stale": True,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Staleness check failed: {e}", "API_500", status_code=500)

    async def _repo_list(self, args: Dict) -> Dict:
        request_id = new_request_id()
        try:
            repos = self.orchestrator.repo_store.list_repositories()
            return self._ok("Repositories listed", {"repos": repos, "total": len(repos)},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"List failed: {e}", "API_500", status_code=500)

    async def _repo_compact(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        import json, yaml
        from pathlib import Path
        from ..core.database import compact_database

        request_id = new_request_id()
        output_format = args.get("output_format", "yaml")
        output_path = args.get("output_path")
        compact_db = args.get("compact_db", True)
        dry_run = args.get("dry_run", False)
        rid = self._resolve_id(repo_id, repo_path)

        try:
            if compact_db and not dry_run:
                compact_database(self.orchestrator.db.conn)
            snapshot = {}
            if rid:
                rows = self.orchestrator.db.conn.execute(
                    "SELECT * FROM files WHERE repository_id=? LIMIT 10", (rid,)
                ).fetchall()
                snapshot = {"repo_id": rid, "sample_files": [dict(r) for r in rows]}
            return self._ok("Compact complete", snapshot, request_id=request_id)
        except Exception as e:
            return self._err(f"Compact failed: {e}", "API_500", status_code=500)

    async def _repo_cleanup(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        from pathlib import Path
        from ..modules.coderepository.core.registry import RegistryManager

        request_id = new_request_id()
        force = args.get("force", False)
        dry_run = args.get("dry_run", False)
        rid = self._resolve_id(repo_id, repo_path)

        if not rid:
            return self._err("No repository found to clean up", "API_404", status_code=404)
        if dry_run:
            return self._ok("Dry run — would delete", {"repo_id": rid}, request_id=request_id)

        try:
            for table in ("files", "directories", "symbols", "edges", "audit_findings",
                          "test_results", "execution_tasks", "file_tree",
                          "disk_usage", "repo_sync_state", "index_stats",
                          "index_query_cache", "embeddings", "edge_hashes"):
                try:
                    self.orchestrator.db.conn.execute(
                        f"DELETE FROM {table} WHERE repository_id=?", (rid,)
                    )
                except Exception:
                    pass
            self.orchestrator.db.conn.execute(
                "DELETE FROM repositories WHERE id=?", (rid,)
            )
            self.orchestrator.db.conn.commit()
            return self._ok("Repository cleaned up", {"repo_id": rid}, request_id=request_id)
        except Exception as e:
            return self._err(f"Cleanup failed: {e}", "API_500", status_code=500)

    async def _repo_dump(self, repo_path: Optional[str], repo_id: Optional[str],
                         args: Dict) -> Dict:
        import json, os
        from pathlib import Path

        request_id = new_request_id()
        rp = repo_path
        if not rp:
            return self._err("repo_path required for dump", "API_400")
        resolved = str(Path(rp).resolve())
        output_dir = args.get("output_dir", os.path.join(os.getcwd(), "codecortex_dumps"))
        fmt = args.get("format", "yaml")
        dry_run = args.get("dry_run", False)

        try:
            repo = self.orchestrator.repo_store.get_repository_by_path(resolved)
            if not repo:
                return self._err("Repository not found", "API_404", status_code=404)
            rid = repo.get("id")

            if dry_run:
                nfiles = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM files WHERE repository_id=?", (rid,)
                ).fetchone()[0]
                return self._ok("Dry run", {"estimated_files": nfiles, "output_dir": output_dir},
                                request_id=request_id)

            # export all tables
            tables = ["files", "directories", "symbols", "edges"]
            dump_data = {"repo_id": rid, "tables": {}}
            for table in tables:
                try:
                    rows = self.orchestrator.db.conn.execute(
                        f"SELECT * FROM {table} WHERE repository_id=?", (rid,)
                    ).fetchall()
                    dump_data["tables"][table] = [dict(r) for r in rows]
                except Exception:
                    pass

            os.makedirs(output_dir, exist_ok=True)
            out = os.path.join(output_dir, f"{rid}.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=2, default=str)

            return self._ok("Dump complete", {"output": out, "repo_id": rid, "tables": list(dump_data["tables"].keys())},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"Dump failed: {e}", "API_500", status_code=500)

    async def _repo_restore(self, args: Dict) -> Dict:
        import json, os
        from pathlib import Path
        from ..modules.coderepository.core.registry import RegistryManager

        request_id = new_request_id()
        source = args.get("source")
        repo_path = args.get("repo_path")
        overwrite = args.get("overwrite", False)
        dry_run = args.get("dry_run", False)

        if not source:
            return self._err("source is required for restore", "API_400")

        final_rp = repo_path or source
        try:
            if dry_run:
                return self._ok("Dry run — would restore from", {"source": source},
                                request_id=request_id)

            if os.path.isdir(source):
                for f in os.listdir(source):
                    if f.endswith(".json"):
                        with open(os.path.join(source, f), encoding="utf-8") as fh:
                            dump = json.load(fh)
                        rid = dump.get("repo_id", "restored_0")
                        for table, rows in dump.get("tables", {}).items():
                            for row in rows:
                                cols = list(row.keys())
                                vals = [row[c] for c in cols]
                                placeholders = ",".join(["?"] * len(vals))
                                try:
                                    self.orchestrator.db.conn.execute(
                                        f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                                        vals,
                                    )
                                except Exception:
                                    pass
                        self.orchestrator.db.conn.commit()
                        RegistryManager.register(final_rp, rid)
                        return self._ok("Restore complete", {"repo_id": rid}, request_id=request_id)

            with open(source, encoding="utf-8") as fh:
                dump = json.load(fh)
            rid = dump.get("repo_id", "restored_0")
            for table, rows in dump.get("tables", {}).items():
                for row in rows:
                    cols = list(row.keys())
                    vals = [row[c] for c in cols]
                    try:
                        self.orchestrator.db.conn.execute(
                            f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(vals))})",
                            vals,
                        )
                    except Exception:
                        pass
            self.orchestrator.db.conn.commit()
            RegistryManager.register(final_rp, rid)
            return self._ok("Restore complete", {"repo_id": rid}, request_id=request_id)
        except Exception as e:
            return self._err(f"Restore failed: {e}", "API_500", status_code=500)

    async def _repo_git(self, repo_path: Optional[str], args: Dict) -> Dict:
        from pathlib import Path
        from ..modules.filesystem.adapters.git import DiskGit

        if not repo_path:
            return self._err("repo_path required for git", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        dry_run = args.get("dry_run", False)

        try:
            params = {
                "subcommand": args.get("subcommand", "status"),
                "args": args.get("args", []),
                "flags": args.get("flags", {}),
                "repo_root": resolved,
            }
            if dry_run:
                return self._ok("Dry run", {"command": params}, request_id=request_id)
            result = DiskGit().execute(params)
            return self._ok("Git executed", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Git failed: {e}", "API_500", status_code=500)

    async def _repo_svn(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.svn import DiskSvn

        request_id = new_request_id()
        dry_run = args.get("dry_run", False)
        try:
            params = {
                "subcommand": args.get("subcommand", "info"),
                "args": args.get("args", []),
                "flags": args.get("flags", {}),
                "target": args.get("target", "."),
            }
            if dry_run:
                return self._ok("Dry run", {"command": params}, request_id=request_id)
            result = DiskSvn().execute(params)
            return self._ok("SVN executed", result, request_id=request_id)
        except Exception as e:
            return self._err(f"SVN failed: {e}", "API_500", status_code=500)

    # ══════════════════════════════════════════════════════════
    # FILESYSTEM DISPATCH (13 actions)
    # ══════════════════════════════════════════════════════════
    async def dispatch_filesystem(self, action: str, path: str, repo_id: Optional[str],
                            args: Dict) -> Dict:
        """Dispatch filesystem actions to internal async methods."""
        action_lower = action.lower()
        if action_lower == "read": return await self._fs_read(path, repo_id, args)
        elif action_lower == "write": return await self._fs_write(path, repo_id, args)
        elif action_lower == "delete": return await self._fs_delete(path, args)
        elif action_lower == "copy": return await self._fs_copy(path, args)
        elif action_lower == "move": return await self._fs_move(path, args)
        elif action_lower == "mkdir": return await self._fs_mkdir(path, args)
        elif action_lower in ("list", "ls"): return await self._fs_list(path, repo_id, args)
        elif action_lower == "search": return await self._fs_search(args)
        elif action_lower == "watch": return await self._fs_watch(args)
        elif action_lower == "usage": return await self._fs_usage(args)
        elif action_lower == "audit": return await self._fs_audit(args)
        elif action_lower == "read_lines": return await self._fs_read_lines(path, repo_id, args)
        elif action_lower == "write_lines": return await self._fs_write_lines(path, repo_id, args)
        else: return self._err(f"Unknown filesystem action: {action}", "API_400")

    async def _fs_read(self, path: Optional[str], repo_id: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path
        from ..core.database.integrity import FileIntegrity

        if not path:
            return self._fs_error(
                "path parameter is required for read operation",
                "API_400", status_code=400,
                recommendations=["Provide a valid file path in the 'path' parameter",
                                 "Use list action to discover available files"],
                context={"action": "read", "provided_path": path},
            )

        resolved = str(Path(path).resolve()) if os.path.isabs(path) else (
            self.orchestrator.fs_service.resolve_repo_path(repo_id, path) if repo_id else str(Path(path).resolve())
        )

        # Check for corrupted file and recover if needed
        health_check = self._ensure_healthy_path(resolved, action="read")
        if health_check.get('corrupted_file_removed'):
            return self._fs_error(
                f"File was corrupted and has been force-removed: {resolved}. "
                f"It cannot be read — it must be recreated.",
                "API_410", status_code=410,
                recommendations=["Use write action to recreate the file with new content",
                                 "If the file contained important data, check backup or VCS history"],
                context={"action": "read", "resolved_path": resolved,
                         "corrupted_file_removed": True},
            )
        if health_check.get('restored_from_repo'):
            # File was corrupted but restored from repo — proceed to read
            pass
        if not health_check['ok']:
            return self._fs_error(
                health_check['error'],
                health_check['code'], status_code=health_check['status'],
                recommendations=health_check['recommendations'],
                context={'action': 'read', **health_check.get('context', {})},
            )

        # Check file existence first
        try:
            exists = os.path.exists(resolved)
        except OSError:
            exists = False
        if not exists:
            return self._fs_error(
                f"File not found: {resolved}",
                "API_404", status_code=404,
                recommendations=["Verify the file path is correct",
                                 "Check if the file was moved or deleted",
                                 "Use list action on the parent directory to see available files"],
                context={"action": "read", "resolved_path": resolved, "repo_id": repo_id},
            )

        if os.path.isdir(resolved):
            return self._fs_error(
                f"Path is a directory, not a file: {resolved}",
                "API_400", status_code=400,
                recommendations=["Provide a file path, not a directory path",
                                 "Use list action to browse directory contents"],
                context={"action": "read", "resolved_path": resolved, "is_directory": True},
            )

        encoding = args.get("encoding", "utf-8")
        offset = args.get("offset", 0)
        limit = args.get("limit")
        request_id = new_request_id()

        try:
            with open(resolved, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            if offset:
                content = content[offset:]
            if limit:
                content = content[:int(limit)]
            rid = self._resolve_id(repo_id, None) or repo_id
            if rid:
                try:
                    FileIntegrity(self.orchestrator.db).update_file(
                        rid, Path(resolved), os.stat(resolved).st_mtime,
                    )
                except Exception:
                    pass
            return self._ok("File read", {"path": resolved, "content": content, "size": len(content)},
                            request_id=request_id)
        except PermissionError:
            return self._fs_error(
                f"Permission denied: cannot read {resolved}",
                "API_403", status_code=403,
                recommendations=["Check file read permissions",
                                 "Try running with elevated privileges",
                                 "Verify the file is not locked by another process"],
                context={"action": "read", "resolved_path": resolved, "encoding": encoding},
            )
        except OSError as e:
            return self._fs_error(
                f"OS error reading file {resolved}: {e}",
                "API_500", status_code=500,
                recommendations=["The file may be corrupted or on an inaccessible filesystem",
                                 "Try copying the file to a different location",
                                 "Run filesystem diagnostics to check disk health"],
                context={"action": "read", "resolved_path": resolved, "error": str(e)},
            )
        except UnicodeDecodeError as e:
            return self._fs_error(
                f"Encoding error reading {resolved} with encoding '{encoding}': {e}",
                "API_400", status_code=400,
                recommendations=[f"Try a different encoding (e.g., encoding='latin-1' or encoding='utf-16')",
                                 "The file may be binary — use binary read mode if applicable"],
                context={"action": "read", "resolved_path": resolved, "encoding": encoding, "error": str(e)},
            )

    def _check_parent_write_chain(self, resolved_path: str) -> Dict[str, Any]:
        """Recursively check parent directory chain for write access.

        Walks up from the file's parent directory to find the first existing ancestor,
        then verifies write access at each level. Returns dict with:
          - ok: True if all parents accessible
          - error: error dict if any parent is inaccessible
          - first_existing: Path of the first existing ancestor
          - missing_parents: List of missing parent paths
        """
        import os
        from pathlib import Path

        resolved = Path(resolved_path)
        parent = resolved.parent

        # Walk up to find first existing parent
        missing_parents = []
        current = parent
        chain = []
        while current.exists() == False or os.access(current, os.F_OK) == False:
            # Check if we can at least see the parent
            if current.parent == current:  # root reached
                break
            missing_parents.append(str(current))
            chain.append(current)
            current = current.parent

        first_existing = current if current.exists() else None

        # Verify write access on the first existing ancestor
        if first_existing and not os.access(first_existing, os.W_OK):
            return {
                "ok": False,
                "error": {
                    "path": str(first_existing),
                    "reason": f"No write permission on parent: {first_existing}",
                },
                "first_existing": first_existing,
                "missing_parents": missing_parents,
            }

        # If there are missing parents, check we can reach them all
        if chain:
            # Verify write access on each level of the chain
            for p in reversed(chain):
                if p.parent.exists() and not os.access(p.parent, os.W_OK):
                    return {
                        "ok": False,
                        "error": {
                            "path": str(p.parent),
                            "reason": f"No write permission to create subdirectory: {p.parent}",
                        },
                        "first_existing": first_existing,
                        "missing_parents": missing_parents,
                    }

        return {
            "ok": True,
            "first_existing": first_existing,
            "missing_parents": missing_parents,
        }

    def _try_restore_from_repository(self, resolved_path: str) -> Optional[Dict[str, Any]]:
        """Try to restore a corrupted file from git or SVN repository.

        Returns {'ok': True, 'method': ...} on restore success,
                None if not in any repository,
                {'ok': False, ...} if restore attempted but failed.
        """
        from pathlib import Path
        from src.modules.filesystem.adapters.git import DiskGit
        from src.modules.filesystem.adapters.svn import DiskSvn

        resolved = Path(resolved_path)

        # Try git
        git_root = DiskGit.find_root(resolved)
        if git_root:
            tracked = DiskGit.is_tracked(git_root, resolved)
            if tracked:
                result = DiskGit.restore_file(git_root, resolved)
                if result.get('ok'):
                    return {'ok': True, 'method': f"git_{result.get('method', 'checkout')}",
                            'source': git_root}
            elif not tracked and DiskGit.is_git_available():
                return None  # In a git repo but not tracked → can't restore

        # Try SVN
        svn_root = DiskSvn.find_root(resolved)
        if svn_root:
            tracked = DiskSvn.is_tracked(svn_root, resolved)
            if tracked:
                result = DiskSvn.restore_file(svn_root, resolved)
                if result.get('ok'):
                    return {'ok': True, 'method': 'svn_revert', 'source': svn_root}

        return None  # Not in any VCS

    def _ensure_healthy_path(self, resolved_path: str, action: str = "write") -> Dict[str, Any]:
        """Verify path health and handle corrupted files on Windows.

        On Windows, corrupted files (WinError 1392) can cause os.path.exists
        and other stat operations to raise OSError.

        Recovery strategy (in order):
        1. Detect if file is in git/SVN repository → try restore from VCS
        2. If restore fails or not in repo → force-remove corrupted file via shell

        Returns {'ok': True} or dict with error details.
        """
        from pathlib import Path

        resolved = Path(resolved_path)

        # Skip if file doesn't exist at all
        try:
            resolved.stat()
        except FileNotFoundError:
            return {'ok': True}
        except PermissionError:
            return {'ok': False,
                    'error': f"Cannot access: {resolved_path} — permission denied",
                    'code': 'API_403', 'status': 403,
                    'recommendations': ['Check file permissions', 'Run with elevated privileges'],
                    'context': {'resolved_path': resolved_path, 'error_type': 'permission'}}
        except OSError as e:
            # File exists but is corrupted/unreadable (WinError 1392)
            # PHASE 1: Try to restore from repository first
            restore_result = self._try_restore_from_repository(resolved_path)
            if restore_result:
                if restore_result.get('ok'):
                    return {'ok': True, 'restored_from_repo': True,
                            'method': restore_result['method'],
                            'source': str(restore_result['source'])}
                # Repository restore was attempted but failed
                return {
                    'ok': False,
                    'error': (
                        f"File is corrupted and repository restore failed: {resolved_path}. "
                        f"Error: {restore_result.get('error', 'unknown')}"
                    ),
                    'code': 'API_500', 'status': 500,
                    'recommendations': [
                        'File is corrupted and git/SVN restore also failed',
                        'Run git/svn commands manually to diagnose the repository state',
                        'If the file is not important, delete it manually via File Explorer',
                    ],
                    'context': {
                        'action': action, 'resolved_path': resolved_path,
                        'restore_error': restore_result.get('error', ''),
                        'restore_method': 'git/svn',
                    },
                }

            # PHASE 2: Not in any repo or restore failed — force-remove corrupted file
            return self._force_remove_corrupted(resolved_path)
        else:
            return {'ok': True}

    def _force_remove_corrupted(self, resolved_path: str) -> Dict[str, Any]:
        """Force-remove a corrupted file via shell commands.

        Uses multi-strategy approach:
        1. cmd /c del /f /q — fast, works for most corrupted files
        2. PowerShell Remove-Item -Force — handles locked/stubborn files (fallback)
        """
        import subprocess
        import os

        strategies = [
            {
                'name': 'cmd del',
                'cmd': f'cmd /c "del /f /q \"{resolved_path}\""',
                'shell': True,
            },
            {
                'name': 'PowerShell Remove-Item',
                'cmd': [
                    'powershell', '-Command',
                    f'Remove-Item -LiteralPath "{resolved_path}" -Force -ErrorAction Stop',
                ],
                'shell': False,
            },
        ]

        last_error = ""
        for strategy in strategies:
            try:
                result = subprocess.run(
                    strategy['cmd'],
                    shell=strategy['shell'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                # Verify the file is actually gone
                if result.returncode == 0 and not os.path.exists(resolved_path):
                    return {'ok': True, 'corrupted_file_removed': True}
                if result.returncode != 0:
                    last_error = f"{strategy['name']}: {result.stderr.strip() or result.stdout.strip()}"
            except subprocess.TimeoutExpired:
                last_error = f"{strategy['name']}: timeout after 10s"
            except Exception as e:
                last_error = f"{strategy['name']}: {e}"

        # All strategies failed
        return {
            'ok': False,
            'error': (
                f"Corrupted file could not be removed after trying all strategies: "
                f"{resolved_path}. Last error: {last_error}"
            ),
            'code': 'API_500', 'status': 500,
            'recommendations': [
                'Delete the file manually via File Explorer or terminal:',
                f'  del /f /q "{resolved_path}"',
                'If that fails, run chkdsk on the drive to repair filesystem errors',
                'Restart your computer — some file locks persist until reboot',
            ],
            'context': {
                'resolved_path': resolved_path,
                'last_error': last_error,
                'manual_command': f'del /f /q "{resolved_path}"',
            },
        }

    async def _fs_write(self, path: Optional[str], repo_id: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path

        if not path:
            return self._fs_error(
                "path parameter is required for write operation",
                "API_400", status_code=400,
                recommendations=["Provide a valid file path in the 'path' parameter",
                                 "Use list action on the parent directory to discover available paths"],
                context={"action": "write", "provided_path": path},
            )

        content = args.get("content", "")
        if not content and not args.get("content"):
            content = ""

        encoding = args.get("encoding", "utf-8")
        atomic = args.get("atomic", True)
        backup = args.get("backup", False)
        create_parents = args.get("create_parents", True)
        overwrite = args.get("overwrite", False)
        request_id = new_request_id()

        # Resolve path safely — handles corrupted files
        try:
            if os.path.isabs(path):
                resolved = str(Path(path).resolve())
            elif repo_id:
                resolved = self.orchestrator.fs_service.resolve_repo_path(repo_id, path)
            else:
                resolved = str(Path(path).resolve())
        except OSError as _res_err:
            return self._fs_error(
                f"Path resolution failed: {path}. The path may be on a corrupted filesystem.",
                "API_500", status_code=500,
                recommendations=["Check the drive for filesystem errors",
                                 "Ensure the path is valid and accessible"],
                context={"action": "write", "provided_path": path, "error": str(_res_err)},
            )

        # Check for corrupted file and recover if needed
        write_check = self._ensure_healthy_path(resolved, action="write")
        if write_check.get('restored_from_repo'):
            # File was corrupted but restored from repo — proceed to overwrite
            pass
        elif write_check.get('corrupted_file_removed'):
            # File was corrupted and force-removed — proceed to create new file
            pass
        elif not write_check['ok']:
            return self._fs_error(
                write_check['error'],
                write_check['code'], status_code=write_check['status'],
                recommendations=write_check['recommendations'],
                context={'action': 'write', **write_check.get('context', {})},
            )

        resolved_path = Path(resolved)

        try:
            # STEP 1: Check if file exists
            if resolved_path.exists():
                if resolved_path.is_dir():
                    return self._fs_error(
                        f"Path is a directory, cannot write to it: {resolved}",
                        "API_400", status_code=400,
                        recommendations=["Provide a file path, not a directory",
                                         "Use mkdir to create directories"],
                        context={"action": "write", "resolved_path": resolved, "is_directory": True},
                    )
                if not overwrite:
                    return self._fs_error(
                        f"File already exists: {resolved}. Use overwrite=true to replace.",
                        "API_409", status_code=409,
                        recommendations=["Set overwrite=true to replace existing file",
                                         "Use a different file path to avoid overwriting",
                                         "Use read action first to check file contents"],
                        context={"action": "write", "resolved_path": resolved, "file_exists": True},
                    )
                # Verify existing file is accessible (handles corrupted/locked files)
                try:
                    with open(resolved, "a") as _f:
                        pass
                except (OSError, PermissionError) as _pe:
                    return self._fs_error(
                        f"Cannot access existing file for overwrite: {resolved}. "
                        f"The file may be corrupted, locked by another process, "
                        f"or has permission issues.",
                        "API_500", status_code=500,
                        recommendations=["Check file permissions or disk health",
                                         "Close any applications that may be locking the file",
                                         "Consider deleting and recreating the file",
                                         "Run filesystem diagnostics (chkdsk on Windows, fsck on Unix)"],
                        context={"action": "write", "resolved_path": resolved,
                                 "error": str(_pe), "file_state": "corrupted_or_locked"},
                    )

            # STEP 2: If file doesn't exist, verify parent folder chain
            if not resolved_path.exists():
                parent = resolved_path.parent
                if not parent.exists():
                    if not create_parents:
                        return self._fs_error(
                            f"Parent directory does not exist: {parent} and create_parents=false",
                            "API_404", status_code=404,
                            recommendations=["Set create_parents=true to auto-create parent directories",
                                             "Use mkdir action to create the parent directory first"],
                            context={"action": "write", "resolved_path": resolved,
                                     "parent_path": str(parent), "create_parents": create_parents},
                        )
                    # Recursive parent write access check
                    parent_check = self._check_parent_write_chain(resolved)
                    if not parent_check["ok"]:
                        err = parent_check["error"]
                        return self._fs_error(
                            f"Cannot create parent directories: {err['reason']}",
                            "API_403", status_code=403,
                            recommendations=["Choose a writable directory for the file",
                                             "Run with elevated privileges if appropriate",
                                             "Verify the target filesystem is not read-only"],
                            context={"action": "write", "resolved_path": resolved,
                                     "failed_path": err["path"], "reason": err["reason"],
                                     "missing_parents": parent_check["missing_parents"]},
                        )
                    # Create parent directories recursively
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                    except PermissionError:
                        return self._fs_error(
                            f"Permission denied: cannot create parent directory {parent}",
                            "API_403", status_code=403,
                            recommendations=["Choose a different directory with write access",
                                             "Run with elevated privileges",
                                             "Check folder permissions on the target path"],
                            context={"action": "write", "resolved_path": resolved,
                                     "parent_path": str(parent)},
                        )
                    except OSError as _mkdir_err:
                        return self._fs_error(
                            f"Cannot create parent directory {parent}: {_mkdir_err}",
                            "API_500", status_code=500,
                            recommendations=["Check disk space availability",
                                             "Verify the path does not contain invalid characters",
                                             "Ensure the filesystem is not read-only"],
                            context={"action": "write", "resolved_path": resolved,
                                     "parent_path": str(parent), "error": str(_mkdir_err)},
                        )

                # Verify parent directory write access
                if not os.access(parent, os.W_OK):
                    return self._fs_error(
                        f"No write permission on parent directory: {parent}",
                        "API_403", status_code=403,
                        recommendations=["Change directory permissions",
                                         "Choose a writable directory",
                                         "Run with elevated privileges"],
                        context={"action": "write", "resolved_path": resolved,
                                 "parent_path": str(parent)},
                    )

                # STEP 3: Touch file before writing (ensures file can be created)
                try:
                    resolved_path.touch(exist_ok=False)
                except FileExistsError:
                    pass  # Race condition — file created between checks, continue
                except PermissionError:
                    return self._fs_error(
                        f"Permission denied: cannot create file {resolved}",
                        "API_403", status_code=403,
                        recommendations=["Check write permissions on the parent directory",
                                         "Try a different file name or location",
                                         "Run with elevated privileges"],
                        context={"action": "write", "resolved_path": resolved},
                    )
                except OSError as _touch_err:
                    return self._fs_error(
                        f"Cannot create file {resolved}: {_touch_err}",
                        "API_500", status_code=500,
                        recommendations=["Check disk space",
                                         "Verify the filename does not contain invalid characters",
                                         "Check if the filesystem is read-only"],
                        context={"action": "write", "resolved_path": resolved,
                                 "error": str(_touch_err)},
                    )

            # STEP 4: Create backup if requested
            if backup and resolved_path.exists():
                import shutil
                import uuid
                backup_path = resolved + ".bak." + str(uuid.uuid4())[:8]
                try:
                    shutil.copy2(resolved, backup_path)
                except Exception as _backup_err:
                    return self._fs_error(
                        f"Failed to create backup of {resolved}: {_backup_err}",
                        "API_500", status_code=500,
                        recommendations=["Check disk space for backup",
                                         "Try with backup=false to skip backup creation"],
                        context={"action": "write", "resolved_path": resolved,
                                 "backup_path": backup_path, "error": str(_backup_err)},
                    )

            # STEP 5: Write content
            if atomic:
                tmp = resolved + ".tmp." + str(os.getpid())
                try:
                    with open(tmp, "w", encoding=encoding) as f:
                        f.write(content)
                    os.replace(tmp, resolved)
                except OSError as _ore:
                    # Clean up temp file on failure
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass
                    return self._fs_error(
                        f"Write failed: cannot replace target file {resolved}. "
                        f"This may indicate file corruption, insufficient permissions, "
                        f"or disk issues.",
                        "API_500", status_code=500,
                        recommendations=["Check disk space and file permissions",
                                         "Try with atomic=false for direct write",
                                         "Ensure no other process is locking the file"],
                        context={"action": "write", "resolved_path": resolved,
                                 "atomic_write": True, "error": str(_ore)},
                    )
            else:
                with open(resolved, "w", encoding=encoding) as f:
                    f.write(content)

            return self._ok("File written", {"path": resolved, "size": len(content)},
                            request_id=request_id)

        except PermissionError:
            return self._fs_error(
                f"Permission denied: cannot write to {resolved}",
                "API_403", status_code=403,
                recommendations=["Check file and directory permissions",
                                 "Run with elevated privileges",
                                 "Choose a writable directory"],
                context={"action": "write", "resolved_path": resolved},
            )
        except OSError as e:
            return self._fs_error(
                f"Write failed — OS error: {e}. "
                f"This may indicate disk corruption, file system issues, "
                f"or permission problems on: {resolved}",
                "API_500", status_code=500,
                recommendations=["Check disk health (chkdsk on Windows, fsck on Unix)",
                                 "Verify sufficient disk space",
                                 "Check if the filesystem is in read-only mode"],
                context={"action": "write", "resolved_path": resolved, "error": str(e)},
            )
        except Exception as e:
            return self._fs_error(
                f"Write failed: {e}",
                "API_500", status_code=500,
                recommendations=["Review the error details and retry the operation",
                                 "Check file system integrity",
                                 "Ensure the target path is valid"],
                context={"action": "write", "resolved_path": resolved, "error": str(e)},
            )

    async def _fs_delete(self, path: Optional[str], args: Dict) -> Dict:
        import os, shutil
        from pathlib import Path

        if not path:
            return self._fs_error(
                "path parameter is required for delete operation",
                "API_400", status_code=400,
                recommendations=["Provide a valid file or directory path in the 'path' parameter",
                                 "Use list action to find available paths"],
                context={"action": "delete", "provided_path": path},
            )

        resolved = str(Path(path).resolve())
        recursive = args.get("recursive", False)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        # Check for corrupted file and recover if needed
        health_check = self._ensure_healthy_path(resolved, action="delete")
        if health_check.get('corrupted_file_removed'):
            return self._ok("Deleted (corrupted file force-removed)", {"path": resolved},
                            request_id=request_id)
        if not health_check['ok']:
            return self._fs_error(
                health_check['error'],
                health_check['code'], status_code=health_check['status'],
                recommendations=health_check['recommendations'],
                context={'action': 'delete', **health_check.get('context', {})},
            )

        # Check existence first
        try:
            exists = os.path.exists(resolved)
        except OSError:
            exists = False
        if not exists and not dry_run:
            return self._fs_error(
                f"Path not found: {resolved}",
                "API_404", status_code=404,
                recommendations=["Verify the path is correct — it may have been moved or deleted",
                                 "Use list action on the parent directory to see available files"],
                context={"action": "delete", "resolved_path": resolved},
            )

        if os.path.isdir(resolved) and not recursive:
            return self._fs_error(
                f"Path is a directory: {resolved}. Use recursive=true to delete directories.",
                "API_400", status_code=400,
                recommendations=["Set recursive=true to delete the directory and its contents",
                                 "Set recursive=false (default) to target individual files"],
                context={"action": "delete", "resolved_path": resolved, "is_directory": True,
                         "recursive": recursive},
            )

        try:
            if dry_run:
                return self._ok("Dry run — would delete", {"path": resolved},
                                request_id=request_id)
            if os.path.isdir(resolved):
                if recursive:
                    shutil.rmtree(resolved)
                else:
                    os.rmdir(resolved)
            else:
                os.remove(resolved)
            return self._ok("Deleted", {"path": resolved}, request_id=request_id)
        except FileNotFoundError:
            return self._fs_error(
                f"Path not found during delete: {resolved}. "
                f"It may have been removed by another process.",
                "API_404", status_code=404,
                recommendations=["Verify the path and retry",
                                 "Check if the file was already deleted"],
                context={"action": "delete", "resolved_path": resolved},
            )
        except PermissionError:
            return self._fs_error(
                f"Permission denied: cannot delete {resolved}",
                "API_403", status_code=403,
                recommendations=["Check file/directory permissions",
                                 "Run with elevated privileges",
                                 "Ensure no other process is using the file"],
                context={"action": "delete", "resolved_path": resolved},
            )
        except OSError as e:
            return self._fs_error(
                f"Delete failed — OS error: {e}. "
                f"The file may be corrupted, locked by another process, "
                f"or there is a disk/permission issue on: {resolved}",
                "API_500", status_code=500,
                recommendations=["Close any applications that may be using the file",
                                 "Check disk for errors",
                                 "Try running with elevated privileges"],
                context={"action": "delete", "resolved_path": resolved, "error": str(e)},
            )

    async def _fs_copy(self, path: Optional[str], args: Dict) -> Dict:
        import os, shutil
        from pathlib import Path

        if not path:
            return self._fs_error(
                "path parameter is required for copy (source)",
                "API_400", status_code=400,
                recommendations=["Provide the source file path in the 'path' parameter",
                                 "Provide the destination path in args.dest"],
                context={"action": "copy", "provided_source": path},
            )

        dest = args.get("dest")
        if not dest:
            return self._fs_error(
                "dest parameter is required for copy (destination)",
                "API_400", status_code=400,
                recommendations=["Provide the destination path in args.dest",
                                 "Example: args={'dest': '/path/to/destination'}"],
                context={"action": "copy", "provided_source": path, "provided_dest": dest},
            )

        src = str(Path(path).resolve())
        dst = str(Path(dest).resolve())
        overwrite = args.get("overwrite", False)
        create_parents = args.get("create_dest_parents", True)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        if not os.path.exists(src):
            return self._fs_error(
                f"Source not found: {src}",
                "API_404", status_code=404,
                recommendations=["Verify the source path is correct",
                                 "Use list action to find available files"],
                context={"action": "copy", "source_path": src, "destination_path": dst},
            )

        try:
            if dry_run:
                return self._ok("Dry run — would copy", {"from": src, "to": dst},
                                request_id=request_id)

            if os.path.exists(dst) and not overwrite:
                return self._fs_error(
                    f"Destination exists: {dst}. Use overwrite=true to replace.",
                    "API_409", status_code=409,
                    recommendations=["Set overwrite=true to replace",
                                     "Choose a different destination path"],
                    context={"action": "copy", "source_path": src, "destination_path": dst},
                )

            # Verify destination parent directory
            if create_parents:
                dst_dir = Path(dst).parent
                if not dst_dir.exists():
                    parent_check = self._check_parent_write_chain(dst)
                    if not parent_check["ok"]:
                        err_info = parent_check["error"]
                        return self._fs_error(
                            f"Cannot create destination parent directories: {err_info['reason']}",
                            "API_403", status_code=403,
                            recommendations=["Choose a writable destination",
                                             "Run with elevated privileges"],
                            context={"action": "copy", "destination_path": dst,
                                     "failed_path": err_info["path"], "reason": err_info["reason"]},
                        )
                if not os.access(dst_dir, os.W_OK):
                    return self._fs_error(
                        f"No write permission on destination directory: {dst_dir}",
                        "API_403", status_code=403,
                        recommendations=["Change destination directory permissions",
                                         "Choose a different destination"],
                        context={"action": "copy", "destination_path": dst,
                                 "parent_path": str(dst_dir)},
                    )
                os.makedirs(str(dst_dir), exist_ok=True)

            if os.path.isdir(src):
                if not overwrite and os.path.exists(dst):
                    return self._fs_error(
                        f"Destination directory exists: {dst}. Use overwrite=true to replace.",
                        "API_409", status_code=409,
                        recommendations=["Set overwrite=true to merge/replace",
                                         "Choose a different destination"],
                        context={"action": "copy", "source_path": src, "destination_path": dst},
                    )
                shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src, dst)
            return self._ok("Copied", {"from": src, "to": dst}, request_id=request_id)

        except PermissionError:
            return self._fs_error(
                f"Permission denied: cannot copy {src} to {dst}",
                "API_403", status_code=403,
                recommendations=["Check permissions on source and destination",
                                 "Run with elevated privileges"],
                context={"action": "copy", "source_path": src, "destination_path": dst},
            )
        except FileNotFoundError:
            return self._fs_error(
                f"Source not found during copy: {src}",
                "API_404", status_code=404,
                recommendations=["Verify the source path and retry"],
                context={"action": "copy", "source_path": src, "destination_path": dst},
            )
        except OSError as e:
            return self._fs_error(
                f"Copy failed — OS error: {e}",
                "API_500", status_code=500,
                recommendations=["Check disk space on destination",
                                 "Verify the filesystem is not read-only",
                                 "For large files, ensure sufficient memory"],
                context={"action": "copy", "source_path": src, "destination_path": dst,
                         "error": str(e)},
            )

    async def _fs_move(self, path: Optional[str], args: Dict) -> Dict:
        import os, shutil
        from pathlib import Path

        if not path:
            return self._fs_error(
                "path parameter is required for move (source)",
                "API_400", status_code=400,
                recommendations=["Provide the source file path in the 'path' parameter",
                                 "Provide the destination path in args.dest"],
                context={"action": "move", "provided_source": path},
            )

        dest = args.get("dest")
        if not dest:
            return self._fs_error(
                "dest parameter is required for move (destination)",
                "API_400", status_code=400,
                recommendations=["Provide the destination path in args.dest",
                                 "Example: args={'dest': '/path/to/destination'}"],
                context={"action": "move", "provided_source": path, "provided_dest": dest},
            )

        src = str(Path(path).resolve())
        dst = str(Path(dest).resolve())
        overwrite = args.get("overwrite", False)
        create_parents = args.get("create_dest_parents", True)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        # Check source exists
        if not os.path.exists(src):
            return self._fs_error(
                f"Source not found: {src}",
                "API_404", status_code=404,
                recommendations=["Verify the source path is correct",
                                 "The file may have been moved or deleted",
                                 "Use list action to find available files"],
                context={"action": "move", "source_path": src, "destination_path": dst},
            )

        if os.path.isdir(src):
            return self._fs_error(
                f"Source is a directory: {src}. Move operation requires a file path.",
                "API_400", status_code=400,
                recommendations=["Use a file path as the source",
                                 "Use copy with recursive=true for directories"],
                context={"action": "move", "source_path": src, "is_directory": True},
            )

        try:
            if dry_run:
                return self._ok("Dry run — would move", {"from": src, "to": dst},
                                request_id=request_id)

            # Check destination
            if os.path.exists(dst) and not overwrite:
                return self._fs_error(
                    f"Destination exists: {dst}. Use overwrite=true to replace.",
                    "API_409", status_code=409,
                    recommendations=["Set overwrite=true to replace the destination",
                                     "Choose a different destination path"],
                    context={"action": "move", "source_path": src, "destination_path": dst},
                )

            # Verify destination parent directory
            dst_parent = Path(dst).parent
            if not dst_parent.exists():
                if not create_parents:
                    return self._fs_error(
                        f"Destination parent directory does not exist: {dst_parent} "
                        f"and create_dest_parents=false",
                        "API_404", status_code=404,
                        recommendations=["Set create_dest_parents=true to auto-create parent directories",
                                         "Use mkdir to create the parent directory first"],
                        context={"action": "move", "destination_path": dst,
                                 "parent_path": str(dst_parent)},
                    )
                # Recursive parent write access check
                parent_check = self._check_parent_write_chain(dst)
                if not parent_check["ok"]:
                    err = parent_check["error"]
                    return self._fs_error(
                        f"Cannot create destination parent directories: {err['reason']}",
                        "API_403", status_code=403,
                        recommendations=["Choose a writable destination directory",
                                         "Run with elevated privileges"],
                        context={"action": "move", "destination_path": dst,
                                 "failed_path": err["path"], "reason": err["reason"]},
                    )
                dst_parent.mkdir(parents=True, exist_ok=True)

            # Verify write access on destination parent
            if not os.access(dst_parent, os.W_OK):
                return self._fs_error(
                    f"No write permission on destination parent directory: {dst_parent}",
                    "API_403", status_code=403,
                    recommendations=["Change destination directory permissions",
                                     "Choose a different destination"],
                    context={"action": "move", "source_path": src, "destination_path": dst,
                             "parent_path": str(dst_parent)},
                )

            shutil.move(src, dst)
            return self._ok("Moved", {"from": src, "to": dst}, request_id=request_id)

        except PermissionError:
            return self._fs_error(
                f"Permission denied: cannot move {src} to {dst}",
                "API_403", status_code=403,
                recommendations=["Check permissions on both source and destination",
                                 "Run with elevated privileges",
                                 "Ensure no other process is using the file"],
                context={"action": "move", "source_path": src, "destination_path": dst},
            )
        except FileNotFoundError:
            return self._fs_error(
                f"Source not found during move: {src}. "
                f"It may have been removed by another process.",
                "API_404", status_code=404,
                recommendations=["Verify the source path and retry",
                                 "Check if the file was already moved or deleted"],
                context={"action": "move", "source_path": src, "destination_path": dst},
            )
        except OSError as e:
            return self._fs_error(
                f"Move failed — OS error: {e}. "
                f"This may indicate cross-filesystem move issues, disk problems, "
                f"or permission restrictions.",
                "API_500", status_code=500,
                recommendations=["For cross-filesystem moves, use copy+delete instead",
                                 "Check disk space on destination filesystem",
                                 "Verify source and destination are accessible"],
                context={"action": "move", "source_path": src, "destination_path": dst,
                         "error": str(e)},
            )

    async def _fs_mkdir(self, path: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path

        if not path:
            return self._err("path required for mkdir", "API_400")
        resolved = str(Path(path).resolve())
        create_parents = args.get("create_parents", True)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        try:
            if dry_run:
                return self._ok("Dry run — would create", {"path": resolved},
                                request_id=request_id)
            os.makedirs(resolved, exist_ok=create_parents)
            return self._ok("Directory created", {"path": resolved}, request_id=request_id)
        except FileExistsError:
            return self._err(f"Directory exists: {resolved}", "API_409", status_code=409)
        except OSError as e:
            return self._err(f"Mkdir failed — OS error: {e}", "API_500", status_code=500)

    async def _fs_list(self, path: Optional[str], repo_id: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path

        rp = path or "."
        try:
            resolved = str(Path(rp).resolve()) if os.path.isabs(rp) else (
                self.orchestrator.fs_service.resolve_repo_path(repo_id, rp) if repo_id else str(Path(rp).resolve())
            )
        except Exception:
            resolved = str(Path(rp).resolve())
        recursive = args.get("recursive", False)
        max_depth = args.get("max_depth")
        include_hidden = args.get("include_hidden", False)
        file_pattern = args.get("file_pattern", "*")
        request_id = new_request_id()

        try:
            entries = []
            if recursive and max_depth:
                for root, dirs, files in os.walk(resolved):
                    depth = root[len(str(resolved)):].count(os.sep)
                    if depth >= int(max_depth):
                        dirs[:] = []
                    for name in files + dirs:
                        fp = os.path.join(root, name)
                        if not include_hidden and name.startswith("."):
                            continue
                        entries.append({
                            "name": name, "path": fp,
                            "is_dir": os.path.isdir(fp),
                            "size": os.path.getsize(fp) if os.path.isfile(fp) else 0,
                        })
            else:
                for name in os.listdir(resolved):
                    if not include_hidden and name.startswith("."):
                        continue
                    fp = os.path.join(resolved, name)
                    entries.append({
                        "name": name, "path": fp,
                        "is_dir": os.path.isdir(fp),
                        "size": os.path.getsize(fp) if os.path.isfile(fp) else 0,
                    })
            return self._ok("Directory listed", {"path": resolved, "entries": entries, "count": len(entries)},
                            request_id=request_id)
        except FileNotFoundError:
            return self._err(f"Not found: {resolved}", "API_404", status_code=404)

    async def _fs_search(self, args: Dict) -> Dict:
        # pyrefly: ignore [missing-import]
        from ..modules.filesystem.adapters.search import DiskSearch

        request_id = new_request_id()
        try:
            params = {
                "root_path": args.get("root_path"),
                "repo_id": args.get("repo_id"),
                "file_pattern": args.get("file_pattern", "*"),
                "file_regex": args.get("file_regex"),
                "content_regex": args.get("content_regex"),
                "content_regex_flags": args.get("content_regex_flags", ""),
                "recursive": args.get("recursive", True),
                "max_depth": args.get("max_depth"),
                "include_hidden": args.get("include_hidden", False),
                "follow_symlinks": args.get("follow_symlinks", False),
                "max_results": args.get("max_results", 100),
                "include_content_snippet": args.get("include_content_snippet", True),
                "exclude_patterns": args.get("exclude_patterns"),
                "replace_text": args.get("replace_text"),
                "dry_run": args.get("dry_run", True),
            }
            result = DiskSearch().search(params)
            return self._ok("Search complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Search failed: {e}", "API_500", status_code=500)

    async def _fs_watch(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.watch import DiskWatcher

        request_id = new_request_id()
        try:
            params = {
                "target": args.get("target", "."),
                "recursive": args.get("recursive", True),
                "events": args.get("events"),
                "poll_interval": args.get("poll_interval", 1),
                "max_events": args.get("max_events", 100),
            }
            result = DiskWatcher.watch(params)
            return self._ok("Watch results", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Watch failed: {e}", "API_500", status_code=500)

    async def _fs_usage(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.df import DiskUsage

        request_id = new_request_id()
        try:
            params = {
                "target": args.get("target", "."),
                "recursive": args.get("recursive", True),
                "depth": args.get("depth", 10),
                "unit": args.get("unit", "auto"),
                "include_hidden": args.get("include_hidden", False),
                "exclude_patterns": args.get("exclude_patterns"),
                "aggregate_by": args.get("aggregate_by", "file"),
                "max_items": args.get("max_items", 100),
            }
            result = DiskUsage.analyze(params)
            return self._ok("Disk usage", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Usage analysis failed: {e}", "API_500", status_code=500)

    async def _fs_audit(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.audit import DiskAudit

        request_id = new_request_id()
        try:
            params = {
                "target": args.get("target", "."),
                "recursive": args.get("recursive", True),
                "severity": args.get("severity"),
                "check_permissions": args.get("check_permissions", True),
                "check_hidden": args.get("check_hidden", True),
                "max_file_size_mb": args.get("max_file_size_mb", 100),
                "exclude_patterns": args.get("exclude_patterns"),
                "limit": args.get("limit", 200),
            }
            result = DiskAudit.audit(params)
            return self._ok("Filesystem audit complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Filesystem audit failed: {e}", "API_500", status_code=500)

    async def _fs_read_lines(self, path: Optional[str], repo_id: Optional[str],
                             args: Dict) -> Dict:
        request_id = new_request_id()
        if not path:
            return self._err("path required for read_lines", "API_400")
        try:
            result = self.orchestrator.fs_service.read_lines(
                path=path,
                start_line=args.get("start_line", 1),
                end_line=args.get("end_line"),
                repo_id=repo_id,
                encoding=args.get("encoding", "utf-8"),
            )
            if "error" in result:
                return self._err(result["error"], "API_500", status_code=500)
            return self._ok("Read lines complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Read lines failed: {e}", "API_500", status_code=500)

    async def _fs_write_lines(self, path: Optional[str], repo_id: Optional[str],
                              args: Dict) -> Dict:
        request_id = new_request_id()
        if not path:
            return self._err("path required for write_lines", "API_400")
        if "content" not in args:
            return self._err("content required for write_lines", "API_400")
        try:
            result = self.orchestrator.fs_service.write_lines(
                path=path,
                start_line=args.get("start_line", 1),
                end_line=args.get("end_line"),
                content=args["content"],
                repo_id=repo_id,
                encoding=args.get("encoding", "utf-8"),
                dry_run=args.get("dry_run", False),
            )
            if "error" in result:
                return self._err(result["error"], "API_500", status_code=500)
            return self._ok("Write lines complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Write lines failed: {e}", "API_500", status_code=500)

    # ══════════════════════════════════════════════════════════
    # CODEBASE DISPATCH (8 actions)
    # Uses shared codebase service
    # ══════════════════════════════════════════════════════════
    async def dispatch_codebase(self, action: str, repo_id: Optional[str],
                                repo_path: Optional[str], args: Dict) -> Dict:
        action_lower = action.lower()
        if action_lower == "search": return await self._cb_search(repo_id, repo_path, args)
        elif action_lower == "audit": return await self._cb_audit(repo_path, repo_id, args)
        elif action_lower == "status": return await self._cb_status(repo_path, repo_id, args)
        elif action_lower == "analyze": return await self._cb_analyze(repo_path, repo_id, args)
        elif action_lower == "index": return await self._cb_index(repo_id, repo_path, args)
        elif action_lower == "test": return await self._cb_test(repo_id, repo_path, args)
        elif action_lower == "refactor": return await self._cb_refactor(repo_id, args)
        elif action_lower == "graph": return await self._cb_graph(repo_id, repo_path, args)
        else: return self._err(f"Unknown codebase action: {action}", "API_400")

    # ══════════════════════════════════════════════════════════
    # SCAFFOLDER DISPATCH (7 actions)
    # Uses shared scaffolder service
    # ══════════════════════════════════════════════════════════
    async def dispatch_scaffolder(self, action: str, args: Dict) -> Dict:
        action_lower = action.lower()
        if action_lower == "list_stacks": return await self._scaffold_list_stacks(args)
        elif action_lower == "get_stack": return await self._scaffold_get_stack(args)
        elif action_lower == "validate_name": return await self._scaffold_validate_name(args)
        elif action_lower == "list_licenses": return await self._scaffold_list_licenses(args)
        elif action_lower == "generate_content": return await self._scaffold_generate_content(args)
        elif action_lower == "generate_class": return await self._scaffold_generate_class(args)
        elif action_lower == "create_project": return await self._scaffold_create_project(args)
        else: return self._err(f"Unknown scaffolder action: {action}", "API_400")

    # ════════════════════════════════════════════════════════
    # UPDATE dispatcher
    # ════════════════════════════════════════════════════════
    def dispatch_update(self, action: str) -> Dict:
        """Dispatch to CodeCortex Auto-Updater.

        Actions: check, status, download, apply, signal, dismiss.
        Uses the orchestrator's update_service (CodeCortexUpdater).
        """
        action_lower = action.lower()
        orch = self.orchestrator
        updater = getattr(orch, "update_service", None)
        if not updater:
            return api_response(
                success=False, status_code=503, message="Auto-update service is not available",
                data=None, error_code="UPDATE_NA",
            )

        try:
            if action_lower == "check":
                result = updater.check()
                return api_response(
                    success=True, data={
                        "local_version": result.local_version,
                        "latest_version": result.latest_version,
                        "update_available": result.update_available,
                        "release_url": result.release_url,
                        "error": result.error,
                        "checked_at": result.checked_at,
                    },
                )

            elif action_lower == "status":
                result = updater.latest_check
                if not result:
                    return api_response(
                        success=True, data={"message": "No version check performed yet. Run 'check' first."},
                    )
                return api_response(
                    success=True, data={
                        "local_version": result.local_version,
                        "latest_version": result.latest_version,
                        "update_available": result.update_available,
                        "release_url": result.release_url,
                        "error": result.error,
                        "checked_at": result.checked_at,
                        "status": updater.status.value,
                    },
                )

            elif action_lower == "download":
                ok = updater.download()
                return api_response(
                    success=ok, data={"downloaded": ok},
                    message="Update downloaded" if ok else "Download failed",
                    status_code=200 if ok else 500,
                )

            elif action_lower == "apply":
                ok = updater.apply()
                return api_response(
                    success=ok, data={"applied": ok},
                    message="Update applied" if ok else "Apply failed",
                    status_code=200 if ok else 500,
                )

            elif action_lower == "signal":
                signal = updater.get_signal()
                if not signal:
                    return api_response(
                        success=True, data={"message": "No update signal file found."},
                    )
                return api_response(
                    success=True, data=signal.to_dict(),
                )

            elif action_lower == "dismiss":
                signal = updater.get_signal()
                if signal:
                    signal.dismiss()
                return api_response(success=True, data={"dismissed": True})

            else:
                return self._err(f"Unknown update action: {action}", "API_400")
        except Exception as e:
            logger.exception("Update action '%s' failed", action)
            return api_response(
                success=False, status_code=500, message=str(e),
                data=None, error_code="UPDATE_ERR",
            )

    # ── scaffolder handlers ────────────────────────────────

    async def _scaffold_list_stacks(self, args: Dict) -> Dict:
        # pyrefly: ignore [missing-import]
        from ..core import get_project_root
        # pyrefly: ignore [missing-import]
        from ..modules.scaffolder.adapters.stack import Stack as StackAdapter

        project_root = get_project_root()
        templates_root = project_root / "datasets" / "templates"
        stack_repo = StackAdapter(templates_root)
        stacks = stack_repo.list_stacks()
        data = []
        for s in stacks:
            data.append({
                "name": s.name,
                "display_name": s.display_name,
                "version": s.version,
                "file_conventions": {
                    "directories": s.file_conventions.directories.value if s.file_conventions else "snake_case",
                    "modules": s.file_conventions.modules if s.file_conventions else "snake_case.py",
                    "classes": s.file_conventions.classes if s.file_conventions else "PascalCase",
                },
                "project_types": [pt.id for pt in s.project_types] if s.project_types else [],
            })
        return self._ok(f"Found {len(data)} stacks", {"stacks": data})

    async def _scaffold_get_stack(self, args: Dict) -> Dict:
        from ..core import get_project_root
        from ..modules.scaffolder.adapters.stack import Stack as StackAdapter

        stack_name = (args.get("stack_name") or "").strip().lower()
        if not stack_name:
            return self._err("stack_name required", "STACK_NAME_REQUIRED")
        project_root = get_project_root()
        templates_root = project_root / "datasets" / "templates"
        stack_repo = StackAdapter(templates_root)
        stack = stack_repo.get_stack(stack_name)
        if stack is None:
            available = [s.name for s in stack_repo.list_stacks()] or ["(none)"]
            return self._err(f"Stack '{stack_name}' not found. Available: {', '.join(available)}",
                             "STACK_NOT_FOUND", status_code=404)
        project_types = [
            {"id": pt.id, "display_name": pt.display_name, "description": pt.description}
            for pt in (stack.project_types or [])
        ]
        return self._ok(f"Stack '{stack.display_name}' found", {
            "stack": {
                "name": stack.name,
                "display_name": stack.display_name,
                "version": stack.version,
                "file_conventions": {
                    "directories": stack.file_conventions.directories.value if stack.file_conventions else "snake_case",
                    "modules": stack.file_conventions.modules if stack.file_conventions else "snake_case.py",
                    "classes": stack.file_conventions.classes if stack.file_conventions else "PascalCase",
                },
                "project_types": project_types,
            },
        })

    async def _scaffold_validate_name(self, args: Dict) -> Dict:
        from ..modules.scaffolder.core.name import Name
        from ..modules.scaffolder.core.exceptions import InvalidNameError

        raw = (args.get("name") or "").strip()
        if not raw:
            return self._err("name required for validate_name", "NAME_REQUIRED")
        try:
            validated = Name.create(raw)
            return self._ok(f"Name '{validated.display}' is valid", {
                "display": validated.display,
                "slug": validated.slug,
                "snake": validated.snake,
                "pascal": validated.pascal,
            })
        except InvalidNameError as exc:
            return self._err(str(exc), "INVALID_NAME", status_code=400)

    async def _scaffold_list_licenses(self, args: Dict) -> Dict:
        from ..modules.scaffolder.core.constants import LicenseIdentifier

        licenses = [
            {"id": member.value, "name": member.name.replace("_", " ").title()}
            for member in LicenseIdentifier
        ]
        return self._ok(f"Found {len(licenses)} license types", {"licenses": licenses})

    async def _scaffold_generate_content(self, args: Dict) -> Dict:
        from ..modules.scaffolder.core.generators import (
            ProjectCategory, gitignore, env_boilerplate, pyproject, readme,
            requirements, dockerfile, docker_compose, setup_sh, setup_bat,
            setup_ps1, logger_py, author_file, ai_ignore,
        )

        file_type = (args.get("file_type") or "").strip().lower()
        if not file_type:
            return self._err("file_type required for generate_content", "FILE_TYPE_REQUIRED")

        generator_map = {
            "gitignore": (gitignore, None),
            "env": (env_boilerplate, None),
            "pyproject": (pyproject, None),
            "readme": (readme, None),
            "requirements": (requirements, None),
            "dockerfile": (dockerfile, None),
            "docker_compose": (docker_compose, None),
            "setup_sh": (setup_sh, None),
            "setup_bat": (setup_bat, None),
            "setup_ps1": (setup_ps1, None),
            "logger_py": (logger_py, None),
            "author_file": (author_file, None),
            "ai_ignore": (ai_ignore, None),
        }

        entry = generator_map.get(file_type)
        if entry is None:
            return self._err(f"Unknown file_type '{file_type}'", "UNKNOWN_FILE_TYPE")

        generator, _ = entry
        category_str = (args.get("project_category") or "standard").strip().lower().replace(" ", "_")
        category_map = {
            "standard": ProjectCategory.STANDARD,
            "data_science": ProjectCategory.DATA_SCIENCE,
            "web_api": ProjectCategory.WEB_API,
            "cli_tool": ProjectCategory.CLI_TOOL,
            "automation": ProjectCategory.AUTOMATION,
            "custom": ProjectCategory.CUSTOM,
        }
        category = category_map.get(category_str, ProjectCategory.STANDARD)
        project_name = args.get("project_name", "My Project")
        author = args.get("author", "Author")
        email = args.get("email", "author@example.com")

        if file_type in ("gitignore", "env", "requirements", "dockerfile", "docker_compose"):
            content = generator(category)
        elif file_type == "pyproject":
            content = generator(author, email, project_name, category, project_name.lower().replace(" ", "_"))
        elif file_type == "readme":
            license_name = args.get("license_name", "MIT")
            content = generator(project_name, author, email, category, license_name)
        elif file_type in ("setup_sh", "setup_bat", "setup_ps1"):
            content = generator(project_name, author)
        elif file_type == "logger_py":
            content = generator(author)
        elif file_type == "author_file":
            content = generator(author, email)
        elif file_type == "ai_ignore":
            content = generator()
        else:
            content = generator(category)

        filename_map = {
            "gitignore": ".gitignore", "env": ".env.example",
            "pyproject": "pyproject.toml", "readme": "README.md",
            "requirements": "requirements.txt", "dockerfile": "Dockerfile",
            "docker_compose": "docker-compose.yml",
            "setup_sh": "bin/setup.sh", "setup_bat": "bin/setup.bat",
            "setup_ps1": "bin/setup.ps1", "logger_py": "src/core/logger.py",
            "author_file": ".author", "ai_ignore": ".aiignore",
        }

        return self._ok(f"Generated {file_type}", {
            "filename": filename_map.get(file_type, file_type),
            "content": content,
            "content_length": len(content),
        })

    async def _scaffold_generate_class(self, args: Dict) -> Dict:
        # pyrefly: ignore [missing-import]
        from ..modules.scaffolder.core.maker import make_class

        type_id = (args.get("type") or "").strip().lower().replace("-", "_")
        name = (args.get("name") or "").strip()
        if not type_id:
            return self._err("type required for generate_class", "TYPE_REQUIRED")
        if not name:
            return self._err("name required for generate_class", "NAME_REQUIRED")

        result = make_class(
            type_id=type_id,
            name=name,
            stack=args.get("stack", "python"),
            module=args.get("module"),
            project_name=args.get("project_name", "Project"),
            author=args.get("author", "Author"),
            target_path=args.get("target_path"),
            overwrite=args.get("overwrite", False),
        )
        if not result["success"]:
            return self._err(result["error"], "MAKE_VALIDATION_ERROR", status_code=400)
        return self._ok(f"Generated {result['type_display']} '{result['class_name']}'", {
            "type": result["type"],
            "type_display": result["type_display"],
            "stack": result["stack"],
            "class_name": result["class_name"],
            "file_name": result["file_name"],
            "relative_path": result["relative_path"],
            "absolute_path": result.get("absolute_path"),
            "content": result["content"],
            "content_length": result["content_length"],
            "written": result["written"],
        })

    async def _scaffold_create_project(self, args: Dict) -> Dict:
        import asyncio
        from ..core import get_project_root, Version
        from ..modules.scaffolder.api.tools import _build_scaffold_services
        from ..modules.scaffolder.core.name import Name
        from ..modules.scaffolder.core.license import License
        from ..modules.scaffolder.core.exceptions import InvalidNameError, ProjectAlreadyExistsError, ScaffoldError
        from ..modules.scaffolder.core.dtos import Project as ProjectDTO
        from ..modules.scaffolder.services.scaffold import Scaffold

        name_raw = (args.get("name") or "").strip()
        if not name_raw:
            return self._err("name required for create_project", "NAME_REQUIRED")
        try:
            validated_name = Name.create(name_raw)
        except InvalidNameError as exc:
            return self._err(str(exc), "INVALID_NAME", status_code=400)

        stack_name = (args.get("stack") or "python").strip().lower()
        project_type_id = (args.get("project_type") or "standard").strip().lower()

        stack_repo, template_repo, engine, file_header = _build_scaffold_services()
        resolved_stack = stack_repo.get_stack(stack_name)
        if resolved_stack is None:
            available = [s.name for s in stack_repo.list_stacks()] or ["(none)"]
            return self._err(f"Stack '{stack_name}' not found. Available: {', '.join(available)}",
                             "STACK_NOT_FOUND", status_code=404)

        resolved_pt = resolved_stack.get_project_type(project_type_id)
        if resolved_pt is None:
            available_pts = resolved_stack.project_type_ids or ["standard"]
            return self._err(f"Project type '{project_type_id}' not found. Available: {', '.join(available_pts)}",
                             "PROJECT_TYPE_NOT_FOUND", status_code=404)

        dry_run = args.get("dry_run", True)
        target_path = args.get("target_path")
        final_target = (
            Path(target_path).resolve()
            if target_path
            else (get_project_root() / "outputs" / "projects" / validated_name.slug).resolve()
        )
        author = args.get("author") or "Author"
        email = args.get("email") or "author@example.com"
        version_str = args.get("version") or "0.1.0"
        license_str = args.get("license") or "MIT"
        overwrite = args.get("overwrite", False)
        include_ai = args.get("include_ai", False)
        include_trainer = args.get("include_trainer", False)
        project_code = args.get("project_code")

        from pathlib import Path

        try:
            resolved_version = Version.from_string(version_str)
        except Exception:
            return self._err(f"Invalid version '{version_str}'", "INVALID_VERSION", status_code=400)

        resolved_license = License.from_string(license_str)

        if dry_run:
            file_count = (
                len(template_repo.get_shared_templates())
                + len(template_repo.get_stack_templates(resolved_stack.name, resolved_pt.id))
            )
            return self._ok(f"Dry-run: project '{validated_name.display}' ready", {
                "dry_run": True,
                "name": {
                    "display": validated_name.display,
                    "slug": validated_name.slug,
                    "snake": validated_name.snake,
                    "pascal": validated_name.pascal,
                },
                "stack": resolved_stack.name,
                "stack_display": resolved_stack.display_name,
                "project_type": resolved_pt.id,
                "project_type_display": resolved_pt.display_name,
                "target_path": str(final_target),
                "author": author,
                "email": email,
                "version": version_str,
                "license": resolved_license.identifier.value,
                "include_ai": include_ai,
                "include_trainer": include_trainer,
                "template_count": file_count,
                "directory_count": 33 + len(resolved_pt.extra_directories),
                "template_context_keys": list(ProjectDTO(
                    name=validated_name,
                    target_path=final_target,
                    stack_name=resolved_stack.name,
                    project_type=resolved_pt,
                    author=author,
                    email=email,
                    version=resolved_version,
                    license=resolved_license,
                    include_ai=include_ai,
                    include_trainer=include_trainer,
                    project_code=project_code,
                ).template_context().keys()),
            })

        project = ProjectDTO(
            name=validated_name,
            target_path=final_target,
            stack_name=resolved_stack.name,
            project_type=resolved_pt,
            author=author,
            email=email,
            version=resolved_version,
            license=resolved_license,
            include_ai=include_ai,
            include_trainer=include_trainer,
            project_code=project_code,
        )

        scaffold_service = Scaffold(stack_repo, template_repo, engine, file_header)
        progress_messages = []

        def _progress(msg: str) -> None:
            progress_messages.append(msg)

        try:
            await asyncio.to_thread(
                scaffold_service.scaffold,
                project,
                progress=_progress,
                overwrite=overwrite,
            )
            return self._ok(f"Project '{validated_name.display}' scaffolded", {
                "dry_run": False,
                "target_path": str(final_target),
                "name": validated_name.display,
                "slug": validated_name.slug,
                "stack": resolved_stack.name,
                "project_type": resolved_pt.id,
                "version": version_str,
                "license": resolved_license.identifier.value,
                "progress": progress_messages,
            })
        except ProjectAlreadyExistsError:
            return self._err(f"Project exists at {final_target}. Set overwrite=true.",
                             "PROJECT_EXISTS", status_code=409)
        except ScaffoldError as exc:
            return self._err(str(exc), "SCAFFOLD_ERROR", status_code=500)
        except Exception as exc:
            logger.error("scaffold_create failed: %s", exc, exc_info=True)
            return self._err(f"Unexpected scaffold error: {exc}", "SCAFFOLD_UNEXPECTED", status_code=500)

    # ── codebase handlers ──────────────────────────────────

    async def _cb_analyze(self, repo_path: Optional[str], repo_id: Optional[str],
                          args: Dict) -> Dict:
        from ..modules.codeanalysis.services.analyze import Analyze, AnalyzeRequest

        target = args.get("target")
        if not target:
            return self._err("args.target required for analyze", "API_400")
        request_id = new_request_id()

        try:
            service = Analyze(db=self.orchestrator.db,
                              fs_service=self.orchestrator.fs_service)
            req = AnalyzeRequest(
                target=target,
                repo_id=repo_id,
                mode=args.get("mode", "auto"),
                max_depth=args.get("max_depth", 3),
                focus=args.get("focus"),
                follow_depth=args.get("follow_depth", 1),
                include_docstring=args.get("include_docstring", True),
                include_comments=args.get("include_comments", False),
                page_size=args.get("page_size", 100),
                cursor=args.get("cursor"),
            )
            result = service.analyze(req)
            return self._ok("Analysis complete", {
                "target": result.target,
                "symbols": [{"name": s.name, "kind": s.kind, "file": s.file_path,
                             "line": s.line_start}
                            for s in result.symbols] if hasattr(result, "symbols") else [],
                "call_graph": result.call_graph if hasattr(result, "call_graph") else {},
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Analyze failed: {e}", "API_500", status_code=500)

    async def _cb_search(self, repo_id: Optional[str], repo_path: Optional[str],
                         args: Dict) -> Dict:
        from ..modules.codeanalysis.services.search import Search, SearchRequest

        query = args.get("query")
        if not query:
            return self._err("args.query required for search", "API_400")
        request_id = new_request_id()

        try:
            service = Search(db=self.orchestrator.db)
            req = SearchRequest(
                query=query,
                repo_id=repo_id,
                limit=args.get("limit", 50),
                file_pattern=args.get("file_pattern", "*"),
                include_content=args.get("include_content", False),
            )
            result = service.search(
                req,
                semantic=args.get("semantic", False),
                graph=args.get("graph_enrichment", False),
                graph_relations=args.get("graph_relations"),
            )
            return self._ok("Search complete", {
                "query": query,
                "results": result.results if hasattr(result, "results") else [],
                "total": result.total if hasattr(result, "total") else 0,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Search failed: {e}", "API_500", status_code=500)

    async def _cb_audit(self, repo_path: Optional[str], repo_id: Optional[str],
                        args: Dict) -> Dict:
        from ..modules.codeanalysis.services.audit import Audit, AuditRequest
        from ..core.database.integrity import FileIntegrity

        target = args.get("target") or repo_path or "."
        request_id = new_request_id()

        try:
            service = Audit(db=self.orchestrator.db,
                            fs_service=self.orchestrator.fs_service)
            req = AuditRequest(
                target=target,
                repository_id=repo_id,
                scan_categories=args.get("scan_categories"),
                severity_threshold=args.get("severity_threshold", "medium"),
                entropy_threshold=args.get("entropy_threshold", 4.5),
                include_comments=args.get("include_comments", False),
                max_file_size_kb=args.get("max_file_size_kb", 1024),
                files=args.get("files"),
                use_ast=args.get("use_ast", True),
                use_aiignore=args.get("use_aiignore", True),
                since=args.get("since"),
            )
            result = service.audit(req)
            # Mark sync
            rid = repo_id or self._resolve_id(None, repo_path)
            if rid:
                try:
                    FileIntegrity(self.orchestrator.db).mark_synced(rid, "audit")
                except Exception:
                    pass
            findings = [{"category": f.category, "severity": f.severity,
                         "file": f.file, "line": f.line, "message": f.message,
                         "remediation": f.remediation}
                        for f in result.findings] if hasattr(result, "findings") else []
            return self._ok(f"Audit complete: {len(findings)} findings",
                            {"target": result.target,
                             "scanned_files": result.scanned_files,
                             "compliance_score": result.compliance_score,
                             "findings": findings,
                             "recommendations": result.recommendations},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"Audit failed: {e}", "API_500", status_code=500)

    async def _cb_graph(self, repo_id: Optional[str], repo_path: Optional[str],
                        args: Dict) -> Dict:
        from ..modules.codegraph.services.coddy import CODDY
        from ..modules.codegraph.services.search import CODDYGraphSearch
        from ..modules.codegraph.services.audit import CODDYGraphAudit
        from ..modules.codegraph.services.trace import CODDYGraphTrace
        from ..modules.codegraph.services.relationship import CODDYGraphRelationship

        sub_action = args.get("sub_action", "build")
        request_id = new_request_id()
        rid = repo_id or self._resolve_id(None, repo_path)
        from pathlib import Path
        rp = str(Path(repo_path).resolve()) if repo_path else None
        if not rp and rid:
            row = self.orchestrator.db.conn.execute("SELECT root_path FROM repositories WHERE id=?", (rid,)).fetchone()
            if row:
                rp = row[0]
        graph_mgr = self.orchestrator.graph_service.graph_manager

        try:
            if sub_action == "build":
                if not rp:
                    return self._err("repo_path required for graph build", "API_400")
                builder = CODDY(self.orchestrator.db, graph_mgr)
                result = await builder.build(
                    repo_path=rp, repo_id=rid,
                    detect_modular=args.get("detect_modular", True),
                    build_dependency_graph=args.get("build_dependency_graph", True),
                    include_core_contracts=args.get("include_core_contracts", True),
                    scan_hmvc_p=args.get("scan_hmvc_p", True),
                    max_depth=args.get("max_depth", 5),
                    use_cache=args.get("use_cache", True),
                )
                return self._ok("Graph built", result, request_id=request_id)

            elif sub_action == "query":
                query_type = args.get("query_type", "callers")
                target = args.get("target")
                if not target:
                    return self._err("args.target required for graph query", "API_400")

                if query_type == "trace_flow":
                    result = await self.orchestrator.graph_service.trace_execution_flow(
                        target, min(args.get("max_depth", 10), 10),
                    )
                elif query_type == "trace_path":
                    tracer = CODDYGraphTrace(self.orchestrator.db, graph_mgr)
                    result = await tracer.trace(
                        repo_id=rid, query_type="trace_path",
                        target_node=target,
                        max_depth=min(args.get("max_depth", 10), 10),
                        end_node=args.get("end_node"),
                        limit=args.get("limit", 20),
                    )
                else:
                    tracer = CODDYGraphTrace(self.orchestrator.db, graph_mgr)
                    result = await tracer.trace(
                        repo_id=rid,
                        query_type=f"find_{query_type}",
                        target_node=target,
                        max_depth=min(args.get("max_depth", 3), 10),
                        limit=args.get("limit", 20),
                    )
                return self._ok("Graph query complete", result, request_id=request_id)

            elif sub_action == "audit":
                auditor = CODDYGraphAudit(self.orchestrator.db, graph_mgr)
                result = await auditor.audit(
                    repo_id=rid,
                    max_depth=5,
                    include_suggestions=True,
                )
                # Also run graph_service audits
                god_nodes = self.orchestrator.graph_service.find_god_nodes(
                    rid, args.get("degree_threshold", 10),
                ) if rid else []
                dead_code = self.orchestrator.graph_service.find_dead_code(
                    rid, rp, args.get("limit", 50),
                ) if rid and rp else []
                return self._ok("Graph audit complete", {
                    "CODDY_audit": result,
                    "god_nodes": god_nodes,
                    "dead_code": dead_code,
                }, request_id=request_id)

            elif sub_action == "relationships":
                target_node = args.get("target_node")
                if not target_node:
                    return self._err("args.target_node required for relationships", "API_400")
                rel = CODDYGraphRelationship(self.orchestrator.db, graph_mgr)
                result = await rel.explore(
                    repo_id=rid, target_node=target_node,
                    relation_type=args.get("relation_type"),
                    direction=args.get("direction", "both"),
                    depth=args.get("depth", 1),
                    modular_type=args.get("modular_type"),
                    include_community=args.get("include_community", False),
                    min_confidence=args.get("min_confidence", "INFERRED"),
                    limit=args.get("limit", 100),
                    cursor=args.get("cursor"),
                )
                return self._ok("Relationships explored", result, request_id=request_id)

            else:
                return self._err(f"Unknown graph sub_action: {sub_action}", "API_400")

        except Exception as e:
            return self._err(f"Graph operation failed: {e}", "API_500", status_code=500)

    async def _cb_status(self, repo_path: Optional[str], repo_id: Optional[str],
                         args: Dict) -> Dict:
        from ..modules.codeanalysis.services.status import Status, StatusRequest
        from ..core.database.index_cache import IndexCache
        from ..core.database.integrity import FileIntegrity

        rp = repo_path or "."
        rid = self._resolve_id(repo_id, repo_path)
        request_id = new_request_id()

        # Try cached path first
        if rid:
            try:
                stats = IndexCache(self.orchestrator.db).get_stats(rid)
                if stats:
                    state = FileIntegrity(self.orchestrator.db).get_sync_state(rid)
                    return self._ok("Status (cached)", {
                        "target": rp, "repo_id": rid,
                        "index_stats": stats,
                        "sync_state": {k: v for k, v in state.items() if k.endswith("_synced_at")},
                        "cached": True,
                    }, request_id=request_id)
            except Exception:
                pass

        try:
            service = Status(db=self.orchestrator.db)
            req = StatusRequest(
                path=rp, repo_id=rid,
                include_metrics=args.get("include_metrics", True),
                include_vcs=args.get("include_vcs", True),
                include_symbols=args.get("include_symbols", True),
                language=args.get("language"),
            )
            result = service.get_status(req)
            data = {
                "target": result.target, "repo_id": result.repo_id,
                "summary": {
                    "files": result.summary.files,
                    "total_lines": result.summary.total_lines,
                    "code_lines": result.summary.code_lines,
                    "comment_ratio": result.summary.comment_ratio,
                } if result.summary else None,
                "symbols": result.symbols,
                "graph_stats": {
                    "nodes": result.graph_stats.nodes,
                    "edges": result.graph_stats.edges,
                } if result.graph_stats else None,
            }
            return self._ok("Status retrieved", data, request_id=request_id)
        except Exception as e:
            return self._err(f"Status failed: {e}", "API_500", status_code=500)

    async def _cb_index(self, repo_id: Optional[str], repo_path: Optional[str],
                        args: Dict) -> Dict:
        sub_action = args.get("sub_action", "build")
        request_id = new_request_id()
        rid = repo_id or self._resolve_id(None, repo_path)

        try:
            if sub_action in ("build", "rebuild"):
                if repo_path:
                    rid = await self.orchestrator.repo_service.sync_repository(
                        repo_path, request_id=request_id,
                    )
                if rid:
                    await self.orchestrator.index_service.index_repository(
                        rid, request_id=request_id,
                    )
                return self._ok("Index built", {"repo_id": rid}, request_id=request_id)

            elif sub_action == "remove":
                if rid:
                    self.orchestrator.db.conn.execute(
                        "DELETE FROM symbols WHERE repository_id=?", (rid,)
                    )
                    self.orchestrator.db.conn.execute(
                        "DELETE FROM edges WHERE repository_id=?", (rid,)
                    )
                    self.orchestrator.db.conn.execute(
                        "DELETE FROM index_stats WHERE repository_id=?", (rid,)
                    )
                    self.orchestrator.db.conn.commit()
                return self._ok("Index removed", {"repo_id": rid}, request_id=request_id)

            elif sub_action == "status":
                if rid:
                    nfiles = self.orchestrator.db.conn.execute(
                        "SELECT COUNT(*) FROM files WHERE repository_id=? AND deleted_at IS NULL",
                        (rid,)
                    ).fetchone()[0]
                    nsym = self.orchestrator.db.conn.execute(
                        "SELECT COUNT(*) FROM symbols WHERE repository_id=?", (rid,)
                    ).fetchone()[0]
                    return self._ok("Index status", {"repo_id": rid, "files": nfiles, "symbols": nsym},
                                    request_id=request_id)
                return self._ok("Index status", {"repo_id": rid, "files": 0, "symbols": 0},
                                request_id=request_id)
            else:
                return self._err(f"Unknown index sub_action: {sub_action}", "API_400")
        except Exception as e:
            return self._err(f"Index operation failed: {e}", "API_500", status_code=500)

    async def _cb_test(self, repo_id: Optional[str], repo_path: Optional[str],
                       args: Dict) -> Dict:
        from ..modules.codetester.services.tester import Tester, CodeTesterRequest
        from ..core.database.integrity import FileIntegrity

        sub_action = args.get("sub_action", "run")
        target = args.get("target_path") or repo_path or "."
        request_id = new_request_id()
        rid = self._resolve_id(repo_id, repo_path)

        try:
            tester = Tester(db=self.orchestrator.db)
            req = CodeTesterRequest(
                target_path=target,
                action=sub_action,
                test_framework=args.get("test_framework", "auto"),
                test_filter=args.get("test_filter"),
                test_names=args.get("test_names"),
                categories=args.get("categories"),
                coverage_format=args.get("coverage_format", "summary"),
                target_symbol=args.get("target_symbol"),
                max_duration=args.get("max_duration", 300),
                async_mode=args.get("async_mode", False),
            )
            result = tester.run_tests(req)
            # Mark synced
            if rid:
                try:
                    FileIntegrity(self.orchestrator.db).mark_synced(rid, "test")
                except Exception:
                    pass
            return self._ok("Test complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Test failed: {e}", "API_500", status_code=500)

    async def _cb_refactor(self, repo_id: Optional[str], args: Dict) -> Dict:
        if not repo_id:
            return self._err("repo_id required for refactor", "API_400")

        sub_action = args.get("sub_action", "rename")
        target_symbol = args.get("target_symbol")
        changes = args.get("changes", {})
        dry_run = args.get("dry_run", True)
        request_id = new_request_id()

        try:
            if sub_action == "impact":
                result = await self.orchestrator.refactor_service.analyze_impact(
                    repo_id, target_symbol, changes.get("source_file"),
                )
            elif sub_action == "rename":
                result = await self.orchestrator.refactor_service.rename_symbol(
                    repo_id, target_symbol, changes.get("source_file"),
                    changes.get("new_name"), dry_run=dry_run,
                )
            elif sub_action == "move":
                result = await self.orchestrator.refactor_service.move_code_element(
                    repo_id, target_symbol, changes.get("source_file"),
                    changes.get("target_file"), dry_run=dry_run,
                )
            elif sub_action == "extract":
                result = await self.orchestrator.refactor_service.extract_function(
                    repo_id, target_symbol, changes, dry_run=dry_run,
                )
            elif sub_action == "inline":
                result = await self.orchestrator.refactor_service.inline_function(
                    repo_id, target_symbol, changes, dry_run=dry_run,
                )
            elif sub_action == "signature":
                result = await self.orchestrator.refactor_service.change_signature(
                    repo_id, target_symbol, changes, dry_run=dry_run,
                )
            else:
                return self._err(f"Unknown refactor sub_action: {sub_action}", "API_400")

            return self._ok(f"Refactor {sub_action} {'preview' if dry_run else 'executed'}",
                            result, request_id=request_id)
        except Exception as e:
            return self._err(f"Refactor failed: {e}", "API_500", status_code=500)

    @staticmethod
    def _run_git_diagnostics(resolved: str, period: str, timeout: int) -> Dict:
        import subprocess
        result = {}
        try:
            subprocess.run(["git", "-C", resolved, "fetch", "--dry-run"],
                           capture_output=True, text=True, timeout=min(timeout, 30))
        except Exception:
            pass
        try:
            logs = subprocess.run(["git", "-C", resolved, "log", "--oneline", f"--since={period}"],
                                  capture_output=True, text=True, timeout=timeout)
            result["recent_commits"] = len(logs.stdout.strip().split("\n")) if logs.stdout.strip() else 0
        except Exception:
            pass
        try:
            status = subprocess.run(["git", "-C", resolved, "status", "--short"],
                                    capture_output=True, text=True, timeout=timeout)
            result["uncommitted"] = len(status.stdout.strip().split("\n")) if status.stdout.strip() else 0
        except Exception:
            pass
        return result
